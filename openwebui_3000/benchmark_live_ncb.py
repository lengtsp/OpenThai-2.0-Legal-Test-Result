#!/usr/bin/env python3
"""Measure live Open WebUI retrieval and RAG answers for NCB audit scenarios."""

from __future__ import annotations

import argparse
import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

from import_ncb_knowledge import DEFAULT_NAME, api, signin


MODEL = "iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b"
MAX_OUTPUT_TOKENS = 2048
SCENARIOS = [
    {
        "id": "access-log-retention",
        "expected": ["17"],
        "question": (
            "ในฐานะ IT Internal Audit ของธนาคาร หากตรวจการเชื่อมต่อและการใช้งานข้อมูล NCB "
            "ควรตรวจ control และหลักฐาน access log อะไร และต้องเก็บบันทึกไว้นานเท่าใด"
        ),
    },
    {
        "id": "data-correction-dispute",
        "expected": ["25", "26", "27"],
        "question": (
            "ลูกค้าโต้แย้งว่าข้อมูลเครดิตไม่ถูกต้อง ธนาคารและบริษัทข้อมูลเครดิตต้องมีขั้นตอนตรวจสอบ "
            "แก้ไข แจ้งผล และบันทึกข้อโต้แย้งอย่างไร"
        ),
    },
    {
        "id": "loan-broker-credit-model",
        "expected": ["24/1", "24/2", "24/3"],
        "question": (
            "ธนาคารรับข้อมูลจากผู้ประกอบธุรกิจเป็นตัวกลางในการจัดหาสินเชื่อ "
            "และจะนำข้อมูลไปทำ credit model ต้องตรวจ consent, onward disclosure "
            "และการทำข้อมูลไม่ให้ระบุตัวบุคคลอย่างไร"
        ),
    },
    {
        "id": "adverse-credit-decision",
        "expected": ["26", "27", "28"],
        "question": (
            "เมื่อธนาคารปฏิเสธสินเชื่อเพราะข้อมูล NCB ต้องแจ้งลูกค้าอย่างไร "
            "ลูกค้ามีสิทธิตรวจสอบหรือขอให้พิจารณาใหม่อย่างไร"
        ),
    },
    {
        "id": "unlawful-disclosure-liability",
        "expected": ["20", "41"],
        "question": (
            "ถ้าพนักงานธนาคารเปิดเผยข้อมูลเครดิตแก่บุคคลที่ไม่มีสิทธิ "
            "ให้วิเคราะห์ข้อกำหนดการเปิดเผย ความรับผิดทางแพ่ง และหลักฐานที่ผู้ตรวจสอบควรรวบรวม"
        ),
    },
]


def section_ids(result: dict) -> list[str]:
    values: list[str] = []
    for metadata in (result.get("metadatas") or [[]])[0]:
        filename = metadata.get("source") or metadata.get("name") or ""
        match = re.search(r"section-(\d+(?:-\d+)?)\.md$", filename)
        if match:
            values.append(match.group(1).replace("-", "/"))
            continue
        raw = metadata.get("section") or metadata.get("section_id")
        if raw:
            values.append(str(raw))
    return list(dict.fromkeys(values))


def find_kb(session: requests.Session, base_url: str, name: str) -> dict:
    result = api(session, "GET", f"{base_url}/api/v1/knowledge/", params={"page": 1})
    for item in result.get("items", []):
        if item.get("name") == name:
            return item
    raise RuntimeError(f"Knowledge Base not found: {name}")


def model_context_tokens(session: requests.Session, base_url: str) -> int | None:
    result = api(session, "GET", f"{base_url}/api/models")
    for item in result.get("data", []):
        if item.get("id") == MODEL:
            value = item.get("max_model_len")
            return int(value) if value else None
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:3000")
    parser.add_argument("--knowledge-name", default=DEFAULT_NAME)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("openwebui_ncb_live_test_20260729"),
    )
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    session = requests.Session()
    signin(session, base_url)
    kb = find_kb(session, base_url, args.knowledge_name)
    context_tokens = model_context_tokens(session, base_url)
    records = []

    for scenario in SCENARIOS:
        retrieval_started = time.perf_counter()
        retrieval = api(
            session,
            "POST",
            f"{base_url}/api/v1/retrieval/query/collection",
            json={
                "collection_names": [kb["id"]],
                "query": scenario["question"],
                "k": 8,
                "k_reranker": 3,
                "r": 0.0,
                "hybrid": True,
                "hybrid_bm25_weight": 0.65,
                "enable_enriched_texts": True,
            },
        )
        retrieval_seconds = time.perf_counter() - retrieval_started
        retrieved = section_ids(retrieval)

        chat_started = time.perf_counter()
        local_chat_id = f"local:{uuid.uuid4()}"
        chat = api(
            session,
            "POST",
            f"{base_url}/api/chat/completions",
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": scenario["question"]}],
                "stream": False,
                "temperature": 0,
                "top_p": 1,
                "max_tokens": MAX_OUTPUT_TOKENS,
                "chat_template_kwargs": {"enable_thinking": False},
                "chat_id": local_chat_id,
                "files": [
                    {
                        "type": "collection",
                        "id": kb["id"],
                        "name": kb["name"],
                    }
                ],
            },
        )
        chat_seconds = time.perf_counter() - chat_started
        answer = chat.get("choices", [{}])[0].get("message", {}).get("content", "")
        finish_reason = chat.get("choices", [{}])[0].get("finish_reason")
        usage = chat.get("usage") or {}

        expected = set(scenario["expected"])
        actual = set(retrieved)
        precision = len(expected & actual) / len(actual) if actual else 0.0
        recall = len(expected & actual) / len(expected) if expected else 1.0
        record = {
            **scenario,
            "retrieved_sections": retrieved,
            "retrieval_precision": precision,
            "retrieval_recall": recall,
            "retrieval_seconds": retrieval_seconds,
            "chat_seconds": chat_seconds,
            "answer_characters": len(answer),
            "finish_reason": finish_reason,
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "answer": answer,
            "retrieval_raw": retrieval,
            "chat_raw": chat,
        }
        records.append(record)
        print(
            f"{scenario['id']}: retrieved={retrieved} "
            f"P={precision:.2f} R={recall:.2f} "
            f"retrieval={retrieval_seconds:.2f}s chat={chat_seconds:.2f}s",
            flush=True,
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "openwebui_base_url": base_url,
        "knowledge_id": kb["id"],
        "knowledge_name": kb["name"],
        "model": MODEL,
        "context_tokens": context_tokens,
        "scenarios": records,
    }
    (args.output_dir / "results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    mean_retrieval = sum(row["retrieval_seconds"] for row in records) / len(records)
    mean_chat = sum(row["chat_seconds"] for row in records) / len(records)
    mean_precision = sum(row["retrieval_precision"] for row in records) / len(records)
    mean_recall = sum(row["retrieval_recall"] for row in records) / len(records)
    lines = [
        "# Live Open WebUI NCB structural-RAG benchmark",
        "",
        f"- Knowledge Base: `{kb['name']}` (`{kb['id']}`)",
        f"- Model: `{MODEL}`",
        f"- vLLM context: "
        f"{f'{context_tokens:,}' if context_tokens is not None else 'unknown'} tokens; "
        "requested maximum answer: "
        f"{MAX_OUTPUT_TOKENS:,} tokens",
        "- Generation: temperature 0, model thinking disabled",
        "- Retrieval: hybrid BM25 0.65 + Qwen3-Embedding-4B, top 8, "
        "BAAI/bge-reranker-v2-m3 top 3",
        f"- Mean retrieval time: {mean_retrieval:.2f}s",
        f"- Mean end-to-end chat time: {mean_chat:.2f}s",
        f"- Macro retrieval precision / recall: {mean_precision:.1%} / {mean_recall:.1%}",
        "",
        "| Scenario | Expected | Retrieved | P | R | Prompt tokens | Output tokens | Finish | Retrieval | Chat |",
        "|---|---|---|---:|---:|---:|---:|---|---:|---:|",
    ]
    for row in records:
        lines.append(
            f"| {row['id']} | {', '.join(row['expected'])} | "
            f"{', '.join(row['retrieved_sections']) or '—'} | "
            f"{row['retrieval_precision']:.0%} | {row['retrieval_recall']:.0%} | "
            f"{row['prompt_tokens'] if row['prompt_tokens'] is not None else 'n/a'} | "
            f"{row['completion_tokens'] if row['completion_tokens'] is not None else 'n/a'} | "
            f"{row['finish_reason'] or 'n/a'} | "
            f"{row['retrieval_seconds']:.2f}s | {row['chat_seconds']:.2f}s |"
        )
    for row in records:
        lines.extend(
            [
                "",
                f"## {row['id']}",
                "",
                f"**Question:** {row['question']}",
                "",
                f"**Expected:** {', '.join(row['expected'])}",
                "",
                f"**Retrieved:** {', '.join(row['retrieved_sections']) or 'none'}",
                "",
                f"**Answer ({row['chat_seconds']:.2f}s, "
                f"{row['completion_tokens'] if row['completion_tokens'] is not None else 'n/a'} "
                f"output tokens, {row['answer_characters']:,} characters):**",
                "",
                row["answer"],
            ]
        )
    (args.output_dir / "report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
