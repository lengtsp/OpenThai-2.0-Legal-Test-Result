#!/usr/bin/env python3
"""Create page-anchored structural chunks for the consolidated Credit Information Act."""

from __future__ import annotations

import argparse
import json
import os
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import fitz
import psycopg2
from psycopg2.extras import Json, execute_values


ROOT = Path(__file__).resolve().parents[2]
PDF_DEFAULT = ROOT / "data/credit_info_act/credit_info_act_update_1_6.pdf"
SOURCE_URL = "https://www.creditinfocommittee.or.th/api/file/pdf/law_act/Credit%20Info%20Act%20update%201-6.pdf"
SOURCE_NAME = "Credit Info Act update 1-6.pdf"
SOURCE_TITLE = "พระราชบัญญัติการประกอบธุรกิจข้อมูลเครดิต พ.ศ. ๒๕๔๕ (รวมฉบับแก้ไข ๑-๖)"
SECTION_RE = re.compile(r"^มาตรา\s*([๐-๙0-9]+(?:/[๐-๙0-9]+)?)")
CHAPTER_RE = re.compile(r"^หมวด\s*([๐-๙0-9]+(?:/[๐-๙0-9]+)?)")
THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
CHAPTER_TITLES = {
    "หมวด ๓": "หมวด ๓ สิทธิและหน้าที่ของบริษัทข้อมูลเครดิต สมาชิกและผู้ใช้บริการ",
}


DDL = """
CREATE TABLE IF NOT EXISTS regulatory_structural_ingest_runs (
    id uuid PRIMARY KEY,
    source_key text NOT NULL,
    source_display_name text NOT NULL,
    source_url text NOT NULL,
    source_file_hash char(64) NOT NULL,
    source_title text NOT NULL,
    extraction_method text NOT NULL,
    page_count integer NOT NULL,
    max_chunk_chars integer NOT NULL,
    chunk_count integer NOT NULL,
    embedding_model text NOT NULL,
    embedding_dimensions integer NOT NULL,
    manifest jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS regulatory_structural_chunks (
    ingest_run_id uuid NOT NULL REFERENCES regulatory_structural_ingest_runs(id) ON DELETE CASCADE,
    chunk_id uuid NOT NULL,
    source_key text NOT NULL,
    root_topic_order integer NOT NULL,
    root_topic text NOT NULL,
    page_start integer NOT NULL CHECK (page_start > 0),
    page_end integer NOT NULL CHECK (page_end >= page_start),
    section_heading text NOT NULL,
    clause_anchor text NOT NULL,
    structural_path text[] NOT NULL,
    content text NOT NULL,
    content_chars integer NOT NULL,
    content_sha256 char(64) NOT NULL,
    embedding real[] NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (ingest_run_id, chunk_id),
    CHECK (cardinality(embedding) > 0)
);

CREATE INDEX IF NOT EXISTS regulatory_structural_chunks_page_idx
    ON regulatory_structural_chunks (source_key, page_start, page_end);
CREATE INDEX IF NOT EXISTS regulatory_structural_chunks_clause_idx
    ON regulatory_structural_chunks (ingest_run_id, clause_anchor);
CREATE INDEX IF NOT EXISTS regulatory_structural_chunks_path_gin_idx
    ON regulatory_structural_chunks USING gin (structural_path);
"""


def normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\x0b", " ")).strip()


def page_body_lines(page: fitz.Page) -> list[str]:
    """Return reading-order lines while excluding amendment footnotes.

    The consolidated PDF places amendment-history notes in separate blocks near
    the bottom of a page. PyMuPDF's plain-text output otherwise appends those
    notes to the active legal section, which harms retrieval and generation.
    """
    result: list[str] = []
    blocks = sorted(
        (block for block in page.get_text("dict")["blocks"] if "lines" in block),
        key=lambda block: (block["bbox"][1], block["bbox"][0]),
    )
    for block in blocks:
        raw_block_lines = [
            normalise("".join(span["text"] for span in line["spans"]))
            for line in block["lines"]
        ]
        raw_block_text = normalise(" ".join(raw_block_lines))
        is_bottom_note = (
            block["bbox"][1] >= page.rect.height * 0.70
            and re.match(r"^[๐-๙0-9]+\s+", raw_block_text)
            and (
                re.match(
                    r"^[๐-๙0-9]+\s+(มาตรา|หมวด|ราชกิจจานุเบกษา)",
                    raw_block_text,
                )
                or "แก้ไขเพิ่มเติมโดยพระราชบัญญัติ" in raw_block_text
            )
        )
        if is_bottom_note:
            continue
        block_lines = []
        for line in block["lines"]:
            # Amendment-note markers are separate 9 pt digit-only superscript
            # spans in this PDF. Exclude the marker from effective law text;
            # retain normal-size Thai item numbers, deadlines, and amounts.
            spans = [
                span
                for span in line["spans"]
                if not (
                    span["size"] <= 9.5
                    and re.fullmatch(r"[๐-๙0-9]+", span["text"].strip())
                )
            ]
            block_lines.append(normalise("".join(span["text"] for span in spans)))
        result.extend(line for line in block_lines if line)
    return result


def db_connection():
    return psycopg2.connect(
        host=os.getenv("OPENGPT_DB_HOST", "127.0.0.1"), port=os.getenv("OPENGPT_DB_PORT", "5432"),
        dbname=os.getenv("OPENGPT_DB_NAME", "opengpt"), user=os.environ["OPENGPT_DB_USER"],
        password=os.environ["OPENGPT_DB_PASSWORD"], connect_timeout=10,
    )


def section_from_heading(line: str, prior: int | None) -> tuple[str, int | None]:
    """Remove PDF footnote numbers fused to a section label (e.g. ๒๔/๑๑๙)."""
    tail = re.sub(r"^มาตรา\s*", "", line).strip()
    slash = re.match(r"([๐-๙0-9]{1,2})/([๐-๙0-9])", tail)
    if slash:
        label = f"{slash.group(1)}/{slash.group(2)}"
        return label, int(slash.group(1).translate(THAI_DIGITS))
    raw = re.match(r"[๐-๙0-9]{1,2}", tail)
    if not raw:
        raise ValueError(f"not a section heading: {line}")
    two = raw.group(0)
    value = int(two.translate(THAI_DIGITS))
    # A trailing footnote is joined to the heading without a space in this PDF:
    # section 2 appears as ๒๑, while section 18 appears as ๑๘๑๒.  Prefer the
    # next sequential section when that disambiguates the first digit.
    if prior is not None and value - prior > 1:
        first = two[0]
        first_value = int(first.translate(THAI_DIGITS))
        if first_value == prior + 1:
            return first, first_value
    return two, value


def structural_sections(pdf_path: Path) -> tuple[list[dict], int]:
    """Segment consecutive PDF text by Thai chapter and section headings.

    The original PDF has no bookmark outline, so this uses the promulgated heading
    hierarchy while retaining every page that contributes to a section.
    """
    document = fitz.open(pdf_path)
    current_chapter = "บททั่วไปและคำนิยาม"
    chapter_order = 0
    current: dict | None = None
    sections: list[dict] = []
    reset_section_sequence = False
    for page_no, page in enumerate(document, start=1):
        lines = page_body_lines(page)
        for position, line in enumerate(lines):
            if not line:
                continue
            chapter = CHAPTER_RE.match(line)
            if chapter:
                if current:
                    sections.append(current)
                    current = None
                # In this consolidation the chapter label and its Thai title are
                # separate PDF lines.  Retain the title in the structural path.
                title_lines: list[str] = []
                for candidate in lines[position + 1:position + 5]:
                    if not candidate:
                        continue
                    if SECTION_RE.match(candidate) or CHAPTER_RE.match(candidate):
                        break
                    title_lines.append(candidate)
                    if len(" ".join(title_lines)) > 160:
                        break
                current_chapter = f"{line} {' '.join(title_lines)}".strip()
                chapter_order += 1
                continue
            if line.startswith("บทเฉพาะกาล"):
                if current:
                    sections.append(current)
                    current = None
                current_chapter = "หมวด ๙ บทเฉพาะกาล"
                chapter_order += 1
                continue
            # Amendment titles begin on the final three pages.  Earlier matches
            # are footnotes citing an amendment, not a new structural document.
            if page_no >= 22 and line.startswith("พระราชบัญญัติการประกอบธุรกิจข้อมูลเครดิต (ฉบับที่"):
                if current:
                    sections.append(current)
                    current = None
                current_chapter = f"ภาคผนวก {line}"
                chapter_order += 1
                reset_section_sequence = True
                continue
            section = SECTION_RE.match(line)
            if section:
                prior = current.get("section_number") if current else (sections[-1].get("section_number") if sections else None)
                if reset_section_sequence:
                    prior = None
                    reset_section_sequence = False
                label, number = section_from_heading(line, prior)
                # A page continuation can begin with a cross-reference such as
                # “มาตรา ๒๐/๑ วรรคสาม ...”; it is not a new section heading.
                if current and prior is not None and number is not None and number < prior:
                    current["lines"].append(line)
                    current["page_end"] = page_no
                    continue
                if current:
                    sections.append(current)
                anchor = f"มาตรา {label}"
                current = {
                    "root_topic": current_chapter,
                    "root_topic_order": chapter_order,
                    "section_heading": anchor,
                    "clause_anchor": anchor,
                    "section_id": label.translate(THAI_DIGITS),
                    "section_number": number,
                    "page_start": page_no,
                    "page_end": page_no,
                    "lines": [line],
                }
            elif current:
                current["lines"].append(line)
                current["page_end"] = page_no
    if current:
        sections.append(current)
    document.close()
    for section in sections:
        section["root_topic"] = CHAPTER_TITLES.get(section["root_topic"], section["root_topic"])
    return sections, page_no


def split_section(section: dict, max_chars: int) -> list[dict]:
    text = normalise(" ".join(section.pop("lines")))
    # Replace the raw PDF heading once more in the stored body.  Footnote marks
    # are visually adjacent to the heading in this source (e.g. “มาตรา ๒๑”),
    # while section_from_heading has already resolved the canonical anchor.
    text = re.sub(r"^มาตรา\s*[๐-๙0-9/]+", section["section_heading"], text, count=1)
    if len(text) <= max_chars:
        return [{**section, "content": text, "part": 1, "parts": 1}]
    clauses = re.split(r"(?<=[\.?!])\s+|(?<=\))\s+(?=\([๐-๙0-9]+\))", text)
    parts: list[str] = []
    active = ""
    for clause in clauses:
        if active and len(active) + len(clause) + 1 > max_chars:
            parts.append(active)
            active = clause
        else:
            active = f"{active} {clause}".strip()
    if active:
        parts.append(active)
    # A single unbroken Thai paragraph may remain; split it deterministically.
    final_parts: list[str] = []
    for item in parts:
        final_parts.extend(item[offset:offset + max_chars] for offset in range(0, len(item), max_chars))
    return [{**section, "content": item, "part": index, "parts": len(final_parts)} for index, item in enumerate(final_parts, start=1)]


def embeddings(texts: list[str], endpoint: str, model: str) -> list[list[float]]:
    import urllib.request

    results: list[list[float]] = []
    for start in range(0, len(texts), 12):
        payload = json.dumps({"model": model, "input": texts[start:start + 12]}, ensure_ascii=False).encode()
        request = urllib.request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=180) as response:
            body = json.loads(response.read().decode())
        results.extend([item["embedding"] for item in sorted(body["data"], key=lambda value: value["index"])])
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=PDF_DEFAULT)
    # The iApp legal-RAG guide recommends one มาตรา per chunk. Section 3 is
    # roughly 5.1k characters, so 8k preserves every active section intact.
    parser.add_argument("--max-chars", type=int, default=8000)
    parser.add_argument("--embedding-endpoint", default="http://127.0.0.1:8082/v1/embeddings")
    parser.add_argument("--embedding-model", default="Qwen3-Embedding-4B")
    parser.add_argument("--out", type=Path, default=ROOT / "data/credit_info_act/structural_manifest.json")
    args = parser.parse_args()
    if not args.pdf.is_file():
        raise FileNotFoundError(args.pdf)
    raw_sections, page_count = structural_sections(args.pdf)
    chunks = [chunk for section in raw_sections for chunk in split_section(section, args.max_chars)]
    vectors = embeddings([chunk["content"] for chunk in chunks], args.embedding_endpoint, args.embedding_model)
    if len(vectors) != len(chunks) or not vectors or len({len(vector) for vector in vectors}) != 1:
        raise RuntimeError("embedding response is missing or has inconsistent dimensions")
    file_hash = sha256(args.pdf.read_bytes()).hexdigest()
    run_id = str(uuid.uuid4())
    topic_counts = Counter(chunk["root_topic"] for chunk in chunks)
    manifest = {
        "ingest_run_id": run_id, "source_key": "credit-info-act-update-1-6", "source_display_name": SOURCE_NAME,
        "source_title": SOURCE_TITLE, "source_url": SOURCE_URL, "source_file_hash": file_hash,
        "pages": page_count, "extraction": "PyMuPDF text layer; Thai chapter/section structural parser",
        "max_chars": args.max_chars, "chunks": len(chunks), "sections": len(raw_sections),
        "embedding_model": args.embedding_model, "embedding_dimensions": len(vectors[0]),
        "topics": [{"topic": topic, "chunks": count} for topic, count in topic_counts.items()],
        "stored_at": datetime.now(timezone.utc).isoformat(),
    }
    rows = []
    for chunk, vector in zip(chunks, vectors):
        path = [SOURCE_TITLE, chunk["root_topic"], chunk["section_heading"]]
        if chunk["parts"] > 1:
            path.append(f"ส่วนที่ {chunk['part']}/{chunk['parts']}")
        content = chunk["content"]
        rows.append((run_id, str(uuid.uuid4()), manifest["source_key"], chunk["root_topic_order"], chunk["root_topic"],
                     chunk["page_start"], chunk["page_end"], chunk["section_heading"], chunk["clause_anchor"], path,
                     content, len(content), sha256(content.encode()).hexdigest(), [float(value) for value in vector],
                     Json({"part": chunk["part"], "parts": chunk["parts"], "section_id": chunk["section_id"], "source_url": SOURCE_URL, "embedding_model": args.embedding_model})))
    with db_connection() as db, db.cursor() as cursor:
        cursor.execute(DDL)
        cursor.execute(
            """INSERT INTO regulatory_structural_ingest_runs
            (id, source_key, source_display_name, source_url, source_file_hash, source_title, extraction_method,
             page_count, max_chunk_chars, chunk_count, embedding_model, embedding_dimensions, manifest)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (run_id, manifest["source_key"], SOURCE_NAME, SOURCE_URL, file_hash, SOURCE_TITLE, manifest["extraction"],
             page_count, args.max_chars, len(rows), args.embedding_model, len(vectors[0]), Json(manifest)),
        )
        execute_values(cursor, """INSERT INTO regulatory_structural_chunks
            (ingest_run_id, chunk_id, source_key, root_topic_order, root_topic, page_start, page_end, section_heading,
             clause_anchor, structural_path, content, content_chars, content_sha256, embedding, metadata) VALUES %s""", rows, page_size=25)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
