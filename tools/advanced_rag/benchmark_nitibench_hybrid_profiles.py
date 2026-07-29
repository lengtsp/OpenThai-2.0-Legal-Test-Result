#!/usr/bin/env python3
"""Cross-law retrieval benchmark over the local VISAI NitiBench vector store."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from datasets import load_dataset


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "rag_webui_8083"))

from benchmark_hybrid_profiles import EmbeddingClient  # noqa: E402
from benchmark_nitibench_rag_modes import law_id  # noqa: E402
from legal_retrieval import LegalHybridRetriever, SearchHit, record_id  # noqa: E402
from nitibench_vector_store import NitiBenchVectorStore  # noqa: E402


class NitiDenseBackend:
    name = "nitibench_sqlite_numpy"

    def __init__(self, store: NitiBenchVectorStore) -> None:
        self.store = store

    def search(self, vector: list[float], top_k: int) -> list[SearchHit]:
        return [
            SearchHit(
                {
                    "id": row["id"],
                    "law_name": row["law_name"],
                    "section": f"มาตรา {row['section_num']}",
                    "content": row["content"],
                    "split": row["split"],
                    "roles": row["roles"],
                },
                row["score"],
                dense_score=row["score"],
                source=self.name,
            )
            for row in self.store.search(vector, top_k)
        ]


def sample_cases(per_law: int, tax_cases: int) -> list[dict[str, Any]]:
    ccl = list(load_dataset("VISAI-AI/nitibench", split="ccl"))
    tax = list(load_dataset("VISAI-AI/nitibench", split="tax"))
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in ccl:
        groups[row["relevant_laws"][0]["law_name"]].append(row)
    output = []
    for law_name in sorted(groups):
        rows = groups[law_name]
        count = min(per_law, len(rows))
        indices = sorted({round(index * (len(rows) - 1) / max(1, count - 1)) for index in range(count)})
        output.extend({**rows[index], "_split": "ccl", "_stratum": law_name} for index in indices)
    count = min(tax_cases, len(tax))
    indices = sorted({round(index * (len(tax) - 1) / max(1, count - 1)) for index in range(count)})
    output.extend({**tax[index], "_split": "tax", "_stratum": "tax"} for index in indices)
    return output


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "queries": len(rows),
        "hit_rate": round(statistics.mean(float(row["first_rank"] is not None) for row in rows), 4),
        "macro_section_recall": round(statistics.mean(row["section_recall"] for row in rows), 4),
        "mrr": round(statistics.mean(1 / row["first_rank"] if row["first_rank"] else 0 for row in rows), 4),
        "mean_latency_ms": round(statistics.mean(row["latency_ms"] for row in rows), 2),
        "p95_latency_ms": round(sorted(row["latency_ms"] for row in rows)[max(0, int(len(rows) * 0.95) - 1)], 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=ROOT / "rag_webui_8083/data/nitibench_vectors.sqlite3")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--per-law", type=int, default=5)
    parser.add_argument("--tax-cases", type=int, default=10)
    args = parser.parse_args()
    store = NitiBenchVectorStore(args.database, collection="nitibench")
    records = [
        {
            "id": row["id"], "law_name": row["law_name"],
            "section": f"มาตรา {row['section_num']}", "content": row["content"],
            "split": row["split"], "roles": row["roles"],
        }
        for row in store.rows
    ]
    cases = sample_cases(args.per_law, args.tax_cases)
    embed = EmbeddingClient("http://127.0.0.1:8082/v1/embeddings", "Qwen3-Embedding-4B")
    # Precompute once so latency below measures retrieval, not the embedding API.
    for case in cases:
        embed(case["question"])
    retriever = LegalHybridRetriever(records, embed_query=embed, dense_backend=NitiDenseBackend(store))
    profiles = ("bm25", "fts5", "dense", "rrf_hybrid", "legal_advanced")
    runs = []
    summaries = {}
    for top_k in (5, 10, 20):
        for profile in profiles:
            group = []
            for case in cases:
                expected = {law_id(case["_split"], law) for law in case["relevant_laws"]}
                started = time.perf_counter()
                hits = retriever.search(case["question"], profile=profile, top_k=top_k, candidate_k=64)
                elapsed = (time.perf_counter() - started) * 1000
                retrieved = [record_id(hit.record) for hit in hits]
                found = expected & set(retrieved)
                first = next((rank for rank, identifier in enumerate(retrieved, 1) if identifier in expected), None)
                row = {
                    "profile": profile, "top_k": top_k, "split": case["_split"],
                    "stratum": case["_stratum"], "question": case["question"],
                    "expected_ids": sorted(expected), "expected_sections": [law["section_num"] for law in case["relevant_laws"]],
                    "retrieved_ids": retrieved, "retrieved_sections": [
                        str(hit.record.get("section", "")).removeprefix("มาตรา ") for hit in hits
                    ],
                    "first_rank": first, "section_recall": round(len(found) / len(expected), 4),
                    "latency_ms": round(elapsed, 2),
                }
                group.append(row)
                runs.append(row)
            summaries[f"{profile}:k{top_k}"] = aggregate(group)
            print(profile, top_k, summaries[f"{profile}:k{top_k}"], flush=True)
    output = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "database": str(args.database), "records": len(records), "queries": len(cases),
        "sampling": {"per_ccl_law": args.per_law, "tax_cases": args.tax_cases},
        "embedding_model": "Qwen3-Embedding-4B", "embedding_latency_excluded": True,
        "summaries": summaries, "runs": runs,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
