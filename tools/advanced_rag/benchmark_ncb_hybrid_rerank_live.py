#!/usr/bin/env python3
"""Exercise the live NCB hybrid retrieval and OpenThai reranker endpoint."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from benchmark_credit_info_act_rag import SCENARIOS


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:8083/api/retrieve")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=6)
    args = parser.parse_args()
    results = []
    args.out.parent.mkdir(parents=True, exist_ok=True)

    def write_checkpoint(complete: bool) -> None:
        output = {
            "created_at": datetime.now(timezone.utc).isoformat(), "endpoint": args.endpoint,
            "top_k": args.top_k, "complete": complete, "runs": results,
            "macro_expected_recall": round(sum(row["expected_recall"] for row in results) / len(results), 4) if results else None,
            "macro_candidate_recall": round(sum(row["candidate_recall"] for row in results) / len(results), 4) if results else None,
            "reranker_statuses": sorted({row["retrieval"].get("status", "") for row in results}),
        }
        args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    for scenario in SCENARIOS:
        started = time.perf_counter()
        response = requests.post(args.endpoint, json={"query": scenario["question"], "top_k": args.top_k}, timeout=600)
        response.raise_for_status()
        payload = response.json()
        sections = [str(hit.get("section", "")).split(" ·", 1)[0].removeprefix("มาตรา ").strip() for hit in payload["hits"]]
        candidate_sections = [str(section).removeprefix("มาตรา ").strip() for section in payload.get("retrieval", {}).get("candidate_sections", [])]
        expected = set(scenario["expected"])
        results.append({
            "scenario": scenario, "sections": sections, "candidate_sections": candidate_sections,
            "expected_recall": round(len(expected & set(sections)) / len(expected), 4),
            "candidate_recall": round(len(expected & set(candidate_sections)) / len(expected), 4),
            "hits": payload["hits"], "retrieval": payload.get("retrieval", {}),
            "wall_seconds": round(time.perf_counter() - started, 2),
        })
        write_checkpoint(complete=False)
        print(scenario["id"], sections, flush=True)
    write_checkpoint(complete=True)
    output = json.loads(args.out.read_text(encoding="utf-8"))
    print(json.dumps({key: output[key] for key in ("macro_candidate_recall", "macro_expected_recall", "reranker_statuses")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
