#!/usr/bin/env python3
"""Extract page-anchored Thai legal sections to JSONL and Open WebUI Markdown."""

from __future__ import annotations

import argparse
import json
import re
import uuid
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import fitz


SECTION_RE = re.compile(r"^มาตรา\s*([๐-๙0-9]+(?:/[๐-๙0-9]+)?)")
CHAPTER_RE = re.compile(r"^หมวด\s*([๐-๙0-9]+(?:/[๐-๙0-9]+)?)")
THAI_TO_ARABIC = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\x0b", " ")).strip()


def body_lines(page: fitz.Page, bottom_note_ratio: float) -> list[str]:
    result: list[str] = []
    blocks = sorted(
        (block for block in page.get_text("dict")["blocks"] if "lines" in block),
        key=lambda block: (block["bbox"][1], block["bbox"][0]),
    )
    for block in blocks:
        lines = [
            normalized("".join(span["text"] for span in line["spans"]))
            for line in block["lines"]
        ]
        text = normalized(" ".join(lines))
        amendment_note = (
            block["bbox"][1] >= page.rect.height * bottom_note_ratio
            and re.match(r"^[๐-๙0-9]+\s+", text)
            and (
                re.match(r"^[๐-๙0-9]+\s+(มาตรา|หมวด|ราชกิจจานุเบกษา)", text)
                or "แก้ไขเพิ่มเติมโดยพระราชบัญญัติ" in text
            )
        )
        if not amendment_note:
            result.extend(line for line in lines if line)
    return result


def canonical_section(line: str, prior: int | None) -> tuple[str, int]:
    tail = re.sub(r"^มาตรา\s*", "", line).strip()
    slash = re.match(r"([๐-๙0-9]{1,2})/([๐-๙0-9])", tail)
    if slash:
        label = f"{slash.group(1)}/{slash.group(2)}"
        return label, int(slash.group(1).translate(THAI_TO_ARABIC))
    raw = re.match(r"[๐-๙0-9]{1,2}", tail)
    if not raw:
        raise ValueError(f"invalid section heading: {line}")
    label = raw.group(0)
    number = int(label.translate(THAI_TO_ARABIC))
    if prior is not None and number - prior > 1:
        first = label[0]
        first_number = int(first.translate(THAI_TO_ARABIC))
        if first_number == prior + 1:
            return first, first_number
    return label, number


def extract(args: argparse.Namespace) -> tuple[list[dict], int]:
    document = fitz.open(args.pdf)
    last_page = min(args.page_end or len(document), len(document))
    topic = "บททั่วไปและคำนิยาม"
    topic_order = 0
    active: dict | None = None
    sections: list[dict] = []
    for page_number in range(args.page_start, last_page + 1):
        page = document[page_number - 1]
        lines = body_lines(page, args.bottom_note_ratio)
        for position, line in enumerate(lines):
            if CHAPTER_RE.match(line):
                if active:
                    sections.append(active)
                    active = None
                title = []
                for candidate in lines[position + 1:position + 5]:
                    if SECTION_RE.match(candidate) or CHAPTER_RE.match(candidate):
                        break
                    title.append(candidate)
                    if len(" ".join(title)) > 160:
                        break
                topic = normalized(f"{line} {' '.join(title)}")
                topic_order += 1
                continue
            match = SECTION_RE.match(line)
            if match:
                prior = active["section_number"] if active else (
                    sections[-1]["section_number"] if sections else None
                )
                label, number = canonical_section(line, prior)
                if active and prior is not None and number < prior:
                    active["lines"].append(line)
                    active["page_end"] = page_number
                    continue
                if active:
                    sections.append(active)
                heading = f"มาตรา {label}"
                active = {
                    "section_id": label.translate(THAI_TO_ARABIC),
                    "section_number": number,
                    "section_heading": heading,
                    "topic": topic,
                    "topic_order": topic_order,
                    "page_start": page_number,
                    "page_end": page_number,
                    "lines": [line],
                }
            elif active:
                active["lines"].append(line)
                active["page_end"] = page_number
    if active:
        sections.append(active)
    document.close()
    return sections, last_page


def recursive_split(text: str, max_chars: int) -> list[str]:
    """Split near legal-text boundaries without cutting through a word.

    Separators are tried from stronger to weaker.  The fallback still chooses
    a Unicode whitespace boundary; a hard cut is used only for a single token
    longer than the configured limit.
    """
    if len(text) <= max_chars:
        return [text]
    minimum = max_chars // 2
    window = text[: max_chars + 1]
    cut = -1
    for pattern in (
        r"\n(?=วรรค|มาตรา|\([๐-๙0-9]+\))",
        r"(?<=[.!?])\s+",
        r"(?<=\))\s+(?=\([๐-๙0-9]+\))",
        r"\s+",
    ):
        matches = list(re.finditer(pattern, window))
        candidates = [match.end() for match in matches if match.end() >= minimum]
        if candidates:
            cut = candidates[-1]
            break
    if cut < 1:
        cut = max_chars
    head = text[:cut].strip()
    tail = text[cut:].strip()
    return [head, *recursive_split(tail, max_chars)] if tail else [head]


def split_section(section: dict, law_name: str, source_url: str, max_chars: int) -> list[dict]:
    lines = section.pop("lines")
    content = normalized(" ".join(lines))
    content = re.sub(r"^มาตรา\s*[๐-๙0-9/]+", section["section_heading"], content, count=1)
    parts = recursive_split(content, max_chars)
    result = []
    for index, part in enumerate(parts, start=1):
        result.append({
            "chunk_id": str(uuid.uuid4()),
            "law_name": law_name,
            **section,
            "source_url": source_url,
            "structural_path": [law_name, section["topic"], section["section_heading"]],
            "part": index,
            "parts": len(parts),
            "content": part,
            "content_chars": len(part),
            "content_sha256": sha256(part.encode()).hexdigest(),
        })
    return result


def quality(chunks: list[dict]) -> dict:
    section_ids = [row["section_id"] for row in chunks if row["part"] == 1]
    failures = []
    warnings = []
    for row in chunks:
        if not row["content"]:
            failures.append(f"{row['chunk_id']}: empty")
        if row["page_start"] < 1 or row["page_end"] < row["page_start"]:
            failures.append(f"{row['chunk_id']}: invalid page anchor")
        if row["part"] == 1 and not row["content"].startswith(row["section_heading"]):
            failures.append(f"{row['chunk_id']}: body does not begin with canonical heading")
    duplicates = sorted({value for value in section_ids if section_ids.count(value) > 1})
    if duplicates:
        failures.append(f"duplicate active section ids: {duplicates}")
    suspicious_topics = sorted(
        {
            row["topic"]
            for row in chunks
            if re.search(r"[ก-๙][๐-๙]{1,2}$", row["topic"])
        }
    )
    if suspicious_topics:
        warnings.append(
            "chapter titles may end with fused footnote markers: "
            + "; ".join(suspicious_topics)
        )
    return {
        "passed": not failures,
        "chunks": len(chunks),
        "sections": len(section_ids),
        "duplicate_section_ids": duplicates,
        "failures": failures,
        "warnings": warnings,
        "manual_review_required": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--law-name", required=True)
    parser.add_argument("--source-url", default="")
    parser.add_argument("--page-start", type=int, default=1)
    parser.add_argument("--page-end", type=int)
    parser.add_argument("--max-chars", type=int, default=4000)
    parser.add_argument("--bottom-note-ratio", type=float, default=0.70)
    args = parser.parse_args()
    if not args.pdf.is_file():
        raise FileNotFoundError(args.pdf)
    sections, last_page = extract(args)
    chunks = [
        chunk
        for section in sections
        for chunk in split_section(section, args.law_name, args.source_url, args.max_chars)
    ]
    report = quality(chunks)
    source_hash = sha256(args.pdf.read_bytes()).hexdigest()
    manifest = {
        "source_filename": args.pdf.name,
        "source_file_hash": source_hash,
        "law_name": args.law_name,
        "source_url": args.source_url,
        "page_start": args.page_start,
        "page_end": last_page,
        "max_chars": args.max_chars,
        "bottom_note_ratio": args.bottom_note_ratio,
        "chunks": len(chunks),
        "sections": len(sections),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    upload_dir = args.out_dir / "openwebui"
    upload_dir.mkdir(exist_ok=True)
    (args.out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.out_dir / "quality.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (args.out_dir / "chunks.jsonl").open("w", encoding="utf-8") as output:
        for row in chunks:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
    grouped: dict[str, list[dict]] = {}
    for row in chunks:
        grouped.setdefault(row["section_id"], []).append(row)
    for section_id, rows in grouped.items():
        first = rows[0]
        content = " ".join(row["content"] for row in rows)
        filename = f"section-{section_id.replace('/', '-')}.md"
        markdown = (
            f"---\nlaw_name: \"{args.law_name}\"\nsection: \"{section_id}\"\n"
            f"source_url: \"{args.source_url}\"\npage_start: {first['page_start']}\n"
            f"page_end: {max(row['page_end'] for row in rows)}\n"
            f"structural_topic: \"{first['topic']}\"\n---\n\n"
            f"# {first['section_heading']}\n\n{content}\n"
        )
        (upload_dir / filename).write_text(markdown, encoding="utf-8")
    print(json.dumps({"manifest": manifest, "quality": report}, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
