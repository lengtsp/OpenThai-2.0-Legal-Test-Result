#!/usr/bin/env python3
"""Benchmark OpenThai 2.0 Legal with long, exact-evidence NCB audit packets."""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


MODEL = "iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b"
DEFAULT_CONTEXT_TOKENS = 12_288
DEFAULT_MAX_OUTPUT_TOKENS = 4_096
THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")

SCENARIOS = [
    {
        "id": "integrated-member-it-audit-program",
        "sections": ["17", "19", "20", "25", "26", "27", "28"],
        "question": (
            "จัดทำแผนตรวจสอบ IT Internal Audit ฉบับละเอียดสำหรับธนาคารที่เป็นสมาชิก NCB "
            "ให้ครอบคลุม governance, data quality, consent/purpose limitation, access control "
            "และ log retention, สิทธิและข้อโต้แย้งของลูกค้า, adverse credit decision, "
            "ขั้นตอน sampling, หลักฐานที่ต้องขอ, วิธีทดสอบ control, เกณฑ์จัดระดับข้อบกพร่อง "
            "และ remediation plan โดยแยก preventive/detective/corrective control "
            "และอ้างมาตราที่เกี่ยวข้องทุกหัวข้อ"
        ),
    },
    {
        "id": "loan-broker-credit-model-governance",
        "sections": ["17", "20", "24/1", "24/2", "24/3", "24/4", "24/5"],
        "question": (
            "ออกแบบ audit work program ฉบับเต็มสำหรับกระบวนการรับข้อมูล NCB ผ่านผู้ประกอบธุรกิจ"
            "เป็นตัวกลางในการจัดหาสินเชื่อและการสร้าง credit model ครอบคลุม consent lifecycle, "
            "onward disclosure, data minimisation/de-identification, model purpose limitation, "
            "access/security/logging, adverse decision, audit evidence, test procedure, "
            "exception examples, risk rating และข้อเสนอแนะ โดยอธิบายผลของมาตรา 24/5 "
            "ที่มีต่อมาตรา 20 และ 28 ให้ชัดเจน"
        ),
    },
    {
        "id": "unlawful-disclosure-incident-response",
        "sections": ["17", "20", "41", "51", "53", "54"],
        "question": (
            "สมมุติพบเหตุพนักงานส่งรายงานข้อมูลเครดิตให้บุคคลภายนอกที่ไม่มีสิทธิ "
            "ให้จัดทำ incident assessment และ audit finding ฉบับละเอียด ตั้งแต่การรักษาหลักฐาน "
            "log/email/file transfer, การพิสูจน์สิทธิและ consent, การแยก civil/criminal exposure, "
            "root cause, affected population, containment, notification/escalation, "
            "corrective action, owner/due date และ follow-up test โดยห้ามสรุปเกินข้อความกฎหมาย"
        ),
    },
    {
        "id": "integrated-criteria-first-guardrail",
        "sections": ["17", "19", "20", "25", "26", "27", "28"],
        "question": (
            "จัดทำ IT Internal Audit work program สำหรับธนาคารที่เป็นสมาชิก NCB "
            "โดยทำตามลำดับนี้อย่างเคร่งครัด: (1) ตาราง Legal Criteria ต้องมีหนึ่งแถวต่อมาตรา "
            "17, 19, 20, 25, 26, 27 และ 28 และห้ามเพิ่มข้อกำหนดที่ไม่มีในตัวบท "
            "(2) ตาราง Control/Evidence/Test แยกจากข้อกฎหมาย (3) ค่า sample size, risk rating, "
            "owner, due date หรือ remediation ทุกค่าที่ผู้ตรวจสอบออกแบบเองต้องติดป้ายว่า "
            "'ข้อเสนอผู้ตรวจสอบ—ไม่ใช่กำหนดเวลาตามกฎหมาย' (4) ตอบภาษาไทยเท่านั้น "
            "(5) ห้ามสร้างหน้าที่แจ้ง regulator หรือ deadline ใหม่ และ "
            "(6) ปิดท้ายด้วย coverage checklist ครบทั้งเจ็ดมาตราและรายการ evidence gap"
        ),
    },
]


def normalise_section(value: str) -> str:
    value = value.translate(THAI_DIGITS)
    value = re.sub(r"\s+", "", value)
    return value


def cited_sections(answer: str) -> list[str]:
    number = r"[๐-๙0-9]+(?:\s*/\s*[๐-๙0-9]+)?"
    separator = r"\s*(?:,\s*(?:(?:and|และ)\s+)?|(?:and|และ)\s+)"
    groups = re.findall(
        rf"(?:มาตรา|sections?)\s*({number}(?:{separator}{number})*)",
        answer,
        flags=re.IGNORECASE,
    )
    matches = []
    for group in groups:
        matches.extend(re.findall(number, group))
    return list(dict.fromkeys(normalise_section(value) for value in matches))


def section_filename(section: str) -> str:
    return f"credit-info-act-section-{section.replace('/', '-')}.md"


def load_packet(knowledge_dir: Path, sections: list[str]) -> str:
    blocks = []
    for section in sections:
        path = knowledge_dir / section_filename(section)
        if not path.is_file():
            raise FileNotFoundError(path)
        blocks.append(path.read_text(encoding="utf-8"))
    return "\n\n---\n\n".join(blocks)


def build_messages(knowledge_dir: Path, scenario: dict) -> list[dict]:
    context = load_packet(knowledge_dir, scenario["sections"])
    system = (
        "คุณคือ OpenThaiGPT-Legal ทำหน้าที่ช่วย IT Internal Audit ของธนาคารไทย "
        "ให้ใช้เฉพาะเอกสารกฎหมายใน <context> เท่านั้น แยกข้อกฎหมาย หลักฐานตรวจสอบ "
        "วิธีทดสอบ control ความเสี่ยง evidence gap และข้อเสนอแนะให้ชัดเจน "
        "อ้างชื่อกฎหมายและเลขมาตราแบบตัวเลขอารบิกทุกประเด็น "
        "หากเอกสารไม่รองรับข้อสรุปใดให้ระบุว่าเป็น evidence gap "
        "ตอบภาษาไทยแบบละเอียดและใช้งานเป็น audit workpaper ได้ทันที\n\n"
        f"<context>\n{context}\n</context>"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": scenario["question"]},
    ]


def get_model_max_len(session: requests.Session, base_url: str) -> int:
    response = session.get(f"{base_url}/v1/models", timeout=30)
    response.raise_for_status()
    for item in response.json().get("data", []):
        if item.get("id") == MODEL:
            return int(item.get("max_model_len") or 0)
    raise RuntimeError(f"Model not found: {MODEL}")


def run_scenario(
    session: requests.Session,
    base_url: str,
    knowledge_dir: Path,
    scenario: dict,
    max_output_tokens: int,
    sampling_overrides: dict | None = None,
) -> dict:
    started = time.perf_counter()
    payload = {
        "model": MODEL,
        "messages": build_messages(knowledge_dir, scenario),
        "temperature": 0,
        "top_p": 1,
        "max_tokens": max_output_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    if sampling_overrides:
        payload.update(sampling_overrides)
    response = session.post(
        f"{base_url}/v1/chat/completions",
        json=payload,
        timeout=1_800,
    )
    elapsed = time.perf_counter() - started
    if not response.ok:
        raise RuntimeError(
            f"{scenario['id']} failed: HTTP {response.status_code}: "
            f"{response.text[:2_000]}"
        )
    raw = response.json()
    choice = raw.get("choices", [{}])[0]
    answer = choice.get("message", {}).get("content", "")
    usage = raw.get("usage") or {}
    expected = set(scenario["sections"])
    cited = set()
    for section in cited_sections(answer):
        parts = section.split("/")
        if section not in expected and len(parts) == 2 and all(p in expected for p in parts):
            cited.update(parts)
        else:
            cited.add(section)
    grounded = cited & expected
    precision = len(grounded) / len(cited) if cited else 0.0
    recall = len(grounded) / len(expected) if expected else 1.0
    return {
        **scenario,
        "cited_sections": sorted(cited),
        "citation_precision": precision,
        "citation_recall": recall,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "answer_characters": len(answer),
        "finish_reason": choice.get("finish_reason"),
        "elapsed_seconds": elapsed,
        "answer": answer,
        "raw": raw,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:3033")
    parser.add_argument(
        "--knowledge-dir",
        type=Path,
        default=Path("data/credit_info_act/openwebui_knowledge"),
    )
    parser.add_argument("--context-tokens", type=int, default=DEFAULT_CONTEXT_TOKENS)
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=DEFAULT_MAX_OUTPUT_TOKENS,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("openthai_12k_long_context_20260729"),
    )
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    session = requests.Session()
    observed_context = get_model_max_len(session, base_url)
    if observed_context != args.context_tokens:
        raise RuntimeError(
            f"Expected context {args.context_tokens:,}, "
            f"but model API reports {observed_context:,}"
        )

    records = []
    for scenario in SCENARIOS:
        record = run_scenario(
            session,
            base_url,
            args.knowledge_dir,
            scenario,
            args.max_output_tokens,
        )
        records.append(record)
        print(
            f"{record['id']}: prompt={record['prompt_tokens']} "
            f"output={record['completion_tokens']} "
            f"finish={record['finish_reason']} "
            f"P={record['citation_precision']:.2f} "
            f"R={record['citation_recall']:.2f} "
            f"time={record['elapsed_seconds']:.2f}s",
            flush=True,
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "model": MODEL,
        "context_tokens": observed_context,
        "max_output_tokens": args.max_output_tokens,
        "thinking_enabled": False,
        "evidence_mode": "exact structural sections",
        "scenarios": records,
    }
    (args.output_dir / "results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    mean_time = sum(row["elapsed_seconds"] for row in records) / len(records)
    mean_precision = sum(row["citation_precision"] for row in records) / len(records)
    mean_recall = sum(row["citation_recall"] for row in records) / len(records)
    lines = [
        "# OpenThai 2.0 Legal — 12k long-context NCB audit benchmark",
        "",
        f"- Model: `{MODEL}`",
        f"- vLLM context: `{observed_context:,}` tokens",
        f"- Maximum output: `{args.max_output_tokens:,}` tokens",
        "- Thinking: disabled",
        "- Evidence mode: exact section-level structural chunks",
        f"- Mean generation time: `{mean_time:.2f}s`",
        f"- Macro citation precision / recall: "
        f"`{mean_precision:.1%}` / `{mean_recall:.1%}`",
        "",
        "| Scenario | Supplied sections | Prompt | Output | Total | Finish | Citation P/R | Time |",
        "|---|---|---:|---:|---:|---|---:|---:|",
    ]
    for row in records:
        lines.append(
            f"| {row['id']} | {', '.join(row['sections'])} | "
            f"{row['prompt_tokens']} | {row['completion_tokens']} | "
            f"{row['total_tokens']} | {row['finish_reason']} | "
            f"{row['citation_precision']:.0%}/{row['citation_recall']:.0%} | "
            f"{row['elapsed_seconds']:.2f}s |"
        )
    for row in records:
        lines.extend(
            [
                "",
                f"## {row['id']}",
                "",
                f"**Question:** {row['question']}",
                "",
                f"**Supplied:** {', '.join(row['sections'])}",
                "",
                f"**Cited:** {', '.join(row['cited_sections']) or 'none'}",
                "",
                f"**Answer ({row['elapsed_seconds']:.2f}s, "
                f"{row['completion_tokens']} output tokens, "
                f"finish={row['finish_reason']}):**",
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
