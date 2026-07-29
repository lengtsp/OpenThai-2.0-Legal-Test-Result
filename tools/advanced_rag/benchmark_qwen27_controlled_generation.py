#!/usr/bin/env python3
"""Compare Qwen3.6-27B with OpenThai using identical final evidence packets.

This benchmark intentionally does not rerun retrieval with Qwen.  It measures
the generator/selector under the same evidence that was already recorded for
the OpenThai evaluation, so retrieval quality is not a confounder.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from benchmark_opengpt_modes_advanced import (
    CHAT_TURNS,
    CITATION_CASES,
    CLOSED_BOOK_CASES,
    ESSAY_CASES,
)


ROOT = Path(__file__).resolve().parent
THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
CITATION_SYSTEM = (
    "You are an expert assistant on Thai law. You are given a legal question and the "
    "exact statutory sections needed to answer it. Analyze the supplied text, then give "
    "the final answer in Thai. Cite ONLY sections present in the provided context, using "
    "each section's exact law_name and bare section number (e.g. 132, 77/1). "
    'Output the final answer as JSON: {"answer": "<Thai answer>", '
    '"citations": [{"law": "<law_name>", "section": "<bare id>"}]}.'
)
CLOSED_BOOK_SYSTEM = (
    "You are an expert on Thai law. You are given ONLY a legal question, with NO reference "
    "material provided. Using your OWN knowledge of Thai statutes, answer in Thai and cite "
    "the specific sections that apply (law name + bare section number, มาตรา). If you are "
    "not confident, say that primary-law verification is required instead of inventing a "
    'section. Output ONLY JSON: {"answer":"<Thai answer>","citations":'
    '[{"law":"<law name>","section":"<bare section number>"}]}.'
)


def normalize_section(value: object) -> str:
    text = str(value or "").translate(THAI_DIGITS).strip()
    return re.sub(r"^มาตรา\s*", "", text)


def parse_json(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    for candidate in (cleaned, *re.findall(r"\{.*\}", cleaned, flags=re.S)):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return {}


def citations_from(parsed: dict[str, Any]) -> list[dict[str, str]]:
    output = []
    for item in parsed.get("citations", []):
        if not isinstance(item, dict):
            continue
        output.append({
            "law": str(item.get("law", "")).strip(),
            "section": normalize_section(item.get("section")),
        })
    return output


def xml_evidence(records: list[dict[str, Any]]) -> str:
    return "\n\n".join(
        f'<law law_name="{row["law_name"]}" section="{normalize_section(row["section"])}">\n'
        f'{row["content"]}\n</law>'
        for row in records
    )


def evidence_text(records: list[dict[str, Any]]) -> str:
    return "\n\n".join(
        f'[{index}] {row["law_name"]} มาตรา {normalize_section(row["section"])}\n{row["content"]}'
        for index, row in enumerate(records, start=1)
    ) or "ไม่มีหลักฐานในคลัง RAG ที่ตรงกับคำถามนี้"


def call(
    endpoint: str,
    model: str,
    messages: list[dict[str, str]],
    *,
    temperature: float,
    top_p: float,
    max_tokens: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    response = requests.post(
        endpoint,
        json={
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "stream": False,
        },
        timeout=1800,
    )
    response.raise_for_status()
    body = response.json()
    message = body["choices"][0].get("message") or {}
    return {
        "raw": message.get("content") or "",
        "reasoning": message.get("reasoning_content") or "",
        "usage": body.get("usage", {}),
        "finish_reason": body["choices"][0].get("finish_reason"),
        "seconds": round(time.perf_counter() - started, 2),
    }


def load_nitibench_records(database: Path) -> dict[tuple[str, str], dict[str, Any]]:
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT law_name, section_num, content FROM chunks WHERE collection='nitibench'"
        ).fetchall()
    return {
        (law, normalize_section(section)): {
            "law_name": law,
            "section": normalize_section(section),
            "content": content,
        }
        for law, section, content in rows
    }


def load_ncb_records(path: Path) -> dict[str, dict[str, Any]]:
    records = json.loads(path.read_text(encoding="utf-8"))
    return {normalize_section(row.get("section")): row for row in records}


def citation_run(
    endpoint: str,
    model: str,
    question: str,
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    result = call(
        endpoint,
        model,
        [
            {"role": "system", "content": CITATION_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Provided context:\n{xml_evidence(evidence)}\n\n"
                    f"Question (ตอบเป็นภาษาไทย):\n{question}"
                ),
            },
        ],
        temperature=0.0,
        top_p=1.0,
        max_tokens=2048,
    )
    parsed = parse_json(result["raw"])
    result.update({
        "answer": parsed.get("answer", ""),
        "citations": citations_from(parsed),
        "json_valid": bool(parsed),
    })
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:8081/v1/chat/completions")
    parser.add_argument("--model", default="Qwen3.6-27B")
    parser.add_argument(
        "--openthai-selection",
        type=Path,
        default=ROOT / "advanced_rag_benchmark_20260729/nitibench_generation_selection.json",
    )
    parser.add_argument(
        "--nitibench-database",
        type=Path,
        default=ROOT / "rag_webui_8083/data/nitibench_vectors.sqlite3",
    )
    parser.add_argument(
        "--ncb-corpus",
        type=Path,
        default=ROOT / "rag_webui_8083/data/ncb_nitibench_hybrid_corpus.json",
    )
    parser.add_argument(
        "--openthai-modes",
        type=Path,
        default=ROOT / "advanced_rag_benchmark_20260729/opengpt_modes.json",
        help="Recorded OpenThai run used to preserve the exact NCB evidence order.",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    ncb = load_ncb_records(args.ncb_corpus)
    niti = load_nitibench_records(args.nitibench_database)
    source_rows = json.loads(args.openthai_selection.read_text(encoding="utf-8"))["results"]
    selection_cases = [row for row in source_rows if row["mode"] == "advanced_hybrid_selection"]
    openthai_modes = json.loads(args.openthai_modes.read_text(encoding="utf-8"))
    ncb_evidence_order = {
        row["case"]["id"]: row["evidence_sections"]
        for row in openthai_modes["groups"]["citation_rag"]
    }

    output: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "endpoint": args.endpoint,
        "comparison_design": "identical final evidence packets; retrieval not rerun",
        "complete": False,
        "groups": {},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)

    def checkpoint() -> None:
        args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    rows = []
    for case in selection_cases:
        expected_pairs = {
            (item["law"], normalize_section(item["section"])) for item in case["expected"]
        }
        expected_records = [niti[pair] for pair in expected_pairs if pair in niti]
        supplied_records = [
            niti[(item["law"], normalize_section(item["section"]))]
            for item in case["supplied"]
            if (item["law"], normalize_section(item["section"])) in niti
        ]
        for mode, records in (
            ("open_book_echo", expected_records),
            ("advanced_hybrid_selection", supplied_records),
        ):
            result = citation_run(args.endpoint, args.model, case["question"], records)
            cited_pairs = {(item["law"], item["section"]) for item in result["citations"]}
            supplied_pairs = {
                (item["law_name"], normalize_section(item["section"])) for item in records
            }
            result.update({
                "case_id": case["case_id"],
                "question": case["question"],
                "mode": mode,
                "expected": case["expected"],
                "supplied": [
                    {"law": item["law_name"], "section": normalize_section(item["section"])}
                    for item in records
                ],
                "citation_recall": round(len(cited_pairs & expected_pairs) / max(1, len(expected_pairs)), 4),
                "citation_precision": round(len(cited_pairs & expected_pairs) / max(1, len(cited_pairs)), 4),
                "grounded_precision": round(len(cited_pairs & supplied_pairs) / max(1, len(cited_pairs)), 4),
            })
            rows.append(result)
            output["groups"]["nitibench"] = rows
            checkpoint()
            print("nitibench", case["case_id"], mode, result["citation_recall"], result["citation_precision"], flush=True)

    rows = []
    for case in CITATION_CASES:
        order = ncb_evidence_order.get(case["id"], case["expected"])
        evidence = [ncb[section] for section in order if section in ncb]
        result = citation_run(args.endpoint, args.model, case["question"], evidence)
        expected_pairs = {
            (row["law_name"], normalize_section(row["section"])) for row in evidence
        }
        cited_pairs = {(item["law"], item["section"]) for item in result["citations"]}
        result.update({
            "case": case,
            "evidence_sections": [normalize_section(row["section"]) for row in evidence],
            "citation_recall": round(len(cited_pairs & expected_pairs) / max(1, len(expected_pairs)), 4),
            "citation_precision": round(len(cited_pairs & expected_pairs) / max(1, len(cited_pairs)), 4),
        })
        rows.append(result)
        output["groups"]["ncb_focused"] = rows
        checkpoint()
        print("ncb", case["id"], result["citation_recall"], result["citation_precision"], flush=True)

    rows = []
    for case in CLOSED_BOOK_CASES:
        result = call(
            args.endpoint,
            args.model,
            [
                {"role": "system", "content": CLOSED_BOOK_SYSTEM},
                {"role": "user", "content": case["question"]},
            ],
            temperature=0.0,
            top_p=1.0,
            max_tokens=2048,
        )
        parsed = parse_json(result["raw"])
        citations = citations_from(parsed)
        cited_sections = {item["section"] for item in citations}
        expected = set(case["expected"])
        result.update({
            "case": case,
            "answer": parsed.get("answer", ""),
            "citations": citations,
            "json_valid": bool(parsed),
            "expected_recall": round(len(cited_sections & expected) / len(expected), 4) if expected else None,
            "evidence_gap_pass": not citations if not expected else None,
        })
        rows.append(result)
        output["groups"]["closed_book"] = rows
        checkpoint()
        print("closed", case["id"], sorted(cited_sections), flush=True)

    rows = []
    for case in ESSAY_CASES:
        evidence = [ncb[section] for section in case["expected"] if case["use_rag"] and section in ncb]
        system = (
            "You are a Thai legal expert. Answer the question with legal analysis and cite "
            "the relevant มาตรา. เมื่อมีหลักฐานประกอบ ให้อ้างเฉพาะมาตราจากหลักฐาน "
            "หากหลักฐานไม่พอให้ระบุช่องว่าง ถ้าไม่มีหลักฐานประกอบ "
            "ให้อ้างได้เฉพาะเลขมาตราที่โจทย์ระบุไว้ชัดแจ้ง ห้ามเติมเลขมาตราอื่นจากการคาดเดา\n\n"
            f"หลักฐานประกอบ:\n{evidence_text(evidence)}"
        )
        result = call(
            args.endpoint,
            args.model,
            [{"role": "system", "content": system}, {"role": "user", "content": case["question"]}],
            temperature=0.7,
            top_p=0.9,
            max_tokens=4096,
        )
        cited = set(re.findall(r"มาตรา\s*([๐-๙0-9]+(?:/[๐-๙0-9]+)?(?:\([๐-๙0-9]+\))?)", result["raw"]))
        cited = {normalize_section(value) for value in cited}
        expected = set(case["expected"])
        result.update({
            "case": case,
            "answer": result["raw"],
            "sections_in_answer": sorted(cited),
            "expected_recall": round(len(cited & expected) / len(expected), 4),
            "evidence_sections": [normalize_section(row["section"]) for row in evidence],
        })
        rows.append(result)
        output["groups"]["legal_essay"] = rows
        checkpoint()
        print("essay", case["id"], result["expected_recall"], flush=True)

    history: list[dict[str, str]] = []
    rows = []
    chat_evidence = [ncb["20"]]
    chat_system = (
        "คุณคือผู้ช่วยสนทนาด้านกฎหมายไทย ตอบเป็นภาษาไทยทุกครั้ง "
        "ให้ข้อมูลที่เข้าใจง่าย ถามกลับเมื่อข้อเท็จจริงสำคัญไม่ครบ "
        "แยกข้อมูลทั่วไปออกจากข้อสรุปทางกฎหมาย และเตือนให้ตรวจฉบับกฎหมายปัจจุบัน"
        f"\n\nหลักฐานที่ค้นได้:\n{evidence_text(chat_evidence)}"
    )
    for turn, question in enumerate(CHAT_TURNS, start=1):
        messages = [{"role": "system", "content": chat_system}, *history, {"role": "user", "content": question}]
        result = call(
            args.endpoint,
            args.model,
            messages,
            temperature=0.7,
            top_p=0.9,
            max_tokens=2048,
        )
        history.extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": result["raw"]},
        ])
        result.update({
            "turn": turn,
            "question": question,
            "answer": result["raw"],
            "evidence_sections": ["20"],
        })
        rows.append(result)
        output["groups"]["general_legal_chat"] = rows
        checkpoint()
        print("chat", turn, flush=True)

    output["complete"] = True
    checkpoint()


if __name__ == "__main__":
    main()
