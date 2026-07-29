#!/usr/bin/env python3
"""Open-book echo versus advanced-hybrid selection on diverse NitiBench laws."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
MODEL = "iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b"
SYSTEM = (
    "You are OpenThaiGPT-Legal, an expert assistant on Thai law. You are given a legal "
    "question and the exact statutory sections needed to answer it. Reason step by step in "
    "English, then give the final answer in Thai. Cite ONLY sections present in the provided "
    "context, using each section's exact law_name and bare section number (e.g. 132, 77/1). "
    'Output the final answer as JSON: {"answer": "<Thai answer>", '
    '"citations": [{"law": "<law_name>", "section": "<bare id>"}]}.'
)
FRAGMENTS = {
    "guardian-consent": "ผู้ิยู่ในปกครองได้ยินยอม",
    "digital-token-offer": "ระหว่างแก้ไขข้อมูลแบบแสดงรายการข้อมูลการเสนอขายโทเคนดิจิทัล",
    "foreign-business-shareholding": "คนต่างด้าวมีข้อจำกัดเรื่องการถือหุ้นหรือไม่",
    "liquidator-fraud": "ผู้ชำระบัญชีของบริษัทจำกัดทุจริต",
    "financial-institution-fraud": "เพื่อลวงให้สถาบันการเงินหรือผู้ถือหุ้นขาดประโยชน์",
    "public-company-email": "หนังสือที่บริษัทมหาชนต้องส่งให้พวกกรรมการ",
    "unlicensed-futures-exchange": "ศูนย์ซื้อขายสัญญาซื้อขายล่วงหน้าโดยไม่ได้รับใบอนุญาต",
    "future-asset-security": "ทรัพย์สินที่ตนมีสิทธิจะได้มาในอนาคตตามสัญญา",
    "tax-animal-feed-import": "SODIUM BICARBONATE FEED GRADE",
}


def load_records(database: Path) -> dict[str, dict]:
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT id, law_name, section_num, content FROM chunks WHERE collection='nitibench'"
        ).fetchall()
    return {
        row[0]: {"id": row[0], "law_name": row[1], "section": row[2], "content": row[3]}
        for row in rows
    }


def parse_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    for candidate in (cleaned, *re.findall(r"\{.*\}", cleaned, flags=re.S)):
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return {}


def call(question: str, evidence: list[dict]) -> dict:
    context = "\n\n".join(
        f'<law law_name="{row["law_name"]}" section="{row["section"]}">\n{row["content"]}\n</law>'
        for row in evidence
    )
    started = time.perf_counter()
    response = requests.post(
        "http://127.0.0.1:3033/v1/chat/completions",
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Provided context:\n{context}\n\nQuestion (ตอบเป็นภาษาไทย):\n{question}"},
            ],
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": 2048,
            "seed": 42,
            "chat_template_kwargs": {"enable_thinking": False},
        },
        timeout=1800,
    )
    response.raise_for_status()
    body = response.json()
    content = body["choices"][0]["message"].get("content") or ""
    parsed = parse_json(content)
    cited = [
        {"law": str(item.get("law", "")), "section": str(item.get("section", ""))}
        for item in parsed.get("citations", [])
        if isinstance(item, dict)
    ]
    return {
        "raw": content,
        "answer": parsed.get("answer", ""),
        "citations": cited,
        "json_valid": bool(parsed),
        "seconds": round(time.perf_counter() - started, 2),
        "usage": body.get("usage", {}),
        "finish_reason": body["choices"][0].get("finish_reason"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retrieval-results", type=Path, required=True)
    parser.add_argument("--database", type=Path, default=ROOT / "rag_webui_8083/data/nitibench_vectors.sqlite3")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.retrieval_results.read_text(encoding="utf-8"))
    runs = [
        row for row in source["runs"]
        if row["profile"] == "legal_advanced" and row["top_k"] == 10
    ]
    records = load_records(args.database)
    cases = []
    for case_id, fragment in FRAGMENTS.items():
        match = next((row for row in runs if fragment in row["question"]), None)
        if match:
            cases.append({"id": case_id, **match})
    output = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "retrieval_profile": "legal_advanced:k10",
        "generation_profile": {"temperature": 0.0, "top_p": 1.0, "max_tokens": 2048, "thinking": False},
        "complete": False,
        "results": [],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    for case in cases:
        expected_rows = [records[identifier] for identifier in case["expected_ids"] if identifier in records]
        selection_rows = [records[identifier] for identifier in case["retrieved_ids"] if identifier in records]
        expected_pairs = {(row["law_name"], row["section"]) for row in expected_rows}
        for mode, evidence in (("open_book_echo", expected_rows), ("advanced_hybrid_selection", selection_rows)):
            result = call(case["question"], evidence)
            cited_pairs = {(row["law"], row["section"]) for row in result["citations"]}
            supplied_pairs = {(row["law_name"], row["section"]) for row in evidence}
            result.update({
                "case_id": case["id"], "question": case["question"], "mode": mode,
                "expected": [{"law": law, "section": section} for law, section in sorted(expected_pairs)],
                "supplied": [{"law": row["law_name"], "section": row["section"]} for row in evidence],
                "citation_recall": round(len(cited_pairs & expected_pairs) / len(expected_pairs), 4),
                "citation_precision": round(len(cited_pairs & expected_pairs) / max(1, len(cited_pairs)), 4),
                "grounded_precision": round(len(cited_pairs & supplied_pairs) / max(1, len(cited_pairs)), 4),
            })
            output["results"].append(result)
            args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
            print(case["id"], mode, result["citation_recall"], result["citation_precision"], flush=True)
    output["complete"] = True
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
