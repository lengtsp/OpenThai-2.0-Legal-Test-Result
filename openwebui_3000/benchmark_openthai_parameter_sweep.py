#!/usr/bin/env python3
"""Controlled decoding-parameter sweep for OpenThai 2.0 Legal."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

from benchmark_openthai_12k_long_context import (
    DEFAULT_CONTEXT_TOKENS,
    MODEL,
    SCENARIOS,
    get_model_max_len,
    run_scenario,
)


PROFILES = [
    {
        "id": "greedy_default",
        "max_output_tokens": 4096,
        "parameters": {
            "temperature": 0,
            "top_p": 1,
        },
    },
    {
        "id": "greedy_repetition_1_05",
        "max_output_tokens": 4096,
        "parameters": {
            "temperature": 0,
            "top_p": 1,
            "repetition_penalty": 1.05,
        },
    },
    {
        "id": "low_temperature_nucleus",
        "max_output_tokens": 4096,
        "parameters": {
            "temperature": 0.15,
            "top_p": 0.9,
            "min_p": 0.05,
            "repetition_penalty": 1.03,
            "seed": 42,
        },
    },
    {
        "id": "recommended_balanced",
        "max_output_tokens": 3072,
        "parameters": {
            "temperature": 0,
            "top_p": 1,
            "repetition_penalty": 1.05,
        },
    },
    {
        "id": "forced_long_completion",
        "max_output_tokens": 5120,
        "parameters": {
            "temperature": 0,
            "top_p": 1,
            "repetition_penalty": 1.03,
            "min_tokens": 4096,
        },
    },
]


def diagnostics(answer: str) -> dict:
    thai_characters = len(re.findall(r"[ก-๙]", answer))
    latin_characters = len(re.findall(r"[A-Za-z]", answer))
    return {
        "thai_characters": thai_characters,
        "latin_characters": latin_characters,
        "thai_to_language_characters": (
            thai_characters / (thai_characters + latin_characters)
            if thai_characters + latin_characters
            else 0.0
        ),
        "auditor_label_count": answer.count(
            "ข้อเสนอผู้ตรวจสอบ—ไม่ใช่กำหนดเวลาตามกฎหมาย"
        ),
        "calendar_dates": re.findall(r"\b\d{1,2}/\d{1,2}/\d{4}\b", answer),
        "mentions_regulator_notification": bool(
            re.search(r"แจ้ง.{0,30}(?:regulator|หน่วยงานกำกับ)", answer, re.I)
        ),
        "mentions_six_months": bool(re.search(r"(?:6|๖)\s*เดือน", answer)),
        "mentions_100_percent_sample": bool(
            re.search(r"(?:100|๑๐๐)\s*%", answer)
        ),
        "ends_with_terminal_punctuation": answer.rstrip().endswith(
            (".", "!", "?", "。", "ฯ", ")", "]", "}", "ครับ", "ค่ะ")
        ),
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
        "--output-dir",
        type=Path,
        default=Path("openthai_parameter_sweep_12k_20260729"),
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

    scenario = SCENARIOS[-1]
    records = []
    for profile in PROFILES:
        record = run_scenario(
            session,
            base_url,
            args.knowledge_dir,
            scenario,
            profile["max_output_tokens"],
            profile["parameters"],
        )
        record["profile"] = profile["id"]
        record["parameters"] = {
            **profile["parameters"],
            "max_tokens": profile["max_output_tokens"],
            "enable_thinking": False,
        }
        record["diagnostics"] = diagnostics(record["answer"])
        records.append(record)
        print(
            f"{profile['id']}: prompt={record['prompt_tokens']} "
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
        "model": MODEL,
        "context_tokens": observed_context,
        "scenario": scenario,
        "profiles": records,
    }
    # Keep raw reruns separate from the curated results.json/report.md, which
    # also contain the Open WebUI replay and post-run Codex judge assessment.
    (args.output_dir / "raw_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = [
        "# OpenThai 2.0 Legal — decoding parameter sweep at 12k context",
        "",
        f"- Model: `{MODEL}`",
        f"- Context: `{observed_context:,}` tokens",
        f"- Controlled scenario: `{scenario['id']}`",
        "- Evidence and prompt are identical across all profiles.",
        "",
        "| Profile | Parameters | Prompt | Output | Finish | Citation P/R | Thai ratio | Labels | Time |",
        "|---|---|---:|---:|---|---:|---:|---:|---:|",
    ]
    for row in records:
        params = ", ".join(f"{k}={v}" for k, v in row["parameters"].items())
        diag = row["diagnostics"]
        lines.append(
            f"| {row['profile']} | {params} | {row['prompt_tokens']} | "
            f"{row['completion_tokens']} | {row['finish_reason']} | "
            f"{row['citation_precision']:.0%}/{row['citation_recall']:.0%} | "
            f"{diag['thai_to_language_characters']:.0%} | "
            f"{diag['auditor_label_count']} | "
            f"{row['elapsed_seconds']:.2f}s |"
        )
    for row in records:
        lines.extend(
            [
                "",
                f"## {row['profile']}",
                "",
                f"**Parameters:** `{json.dumps(row['parameters'], ensure_ascii=False)}`",
                "",
                f"**Diagnostics:** `{json.dumps(row['diagnostics'], ensure_ascii=False)}`",
                "",
                f"**Answer ({row['elapsed_seconds']:.2f}s, "
                f"{row['completion_tokens']} output tokens, "
                f"finish={row['finish_reason']}):**",
                "",
                row["answer"],
            ]
        )
    (args.output_dir / "raw_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
