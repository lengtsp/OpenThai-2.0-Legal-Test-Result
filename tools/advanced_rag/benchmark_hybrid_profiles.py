#!/usr/bin/env python3
"""Benchmark lexical, dense and hybrid legal retrieval profiles."""

from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "rag_webui_8083"))

from legal_retrieval import (  # noqa: E402
    LegalHybridRetriever,
    MemoryDenseBackend,
    QdrantDenseBackend,
    section_number,
)


def load_ncb_scenarios() -> list[dict[str, Any]]:
    path = ROOT / "benchmark_credit_info_act_rag.py"
    spec = importlib.util.spec_from_file_location("ncb_benchmark_source", path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load scenarios from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.SCENARIOS)


class EmbeddingClient:
    def __init__(self, endpoint: str, model: str) -> None:
        self.endpoint = endpoint
        self.model = model
        self.cache: dict[str, list[float]] = {}

    def __call__(self, text: str) -> list[float]:
        if text in self.cache:
            return self.cache[text]
        payload = json.dumps({"model": self.model, "input": text}, ensure_ascii=False).encode()
        request = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            vector = json.loads(response.read().decode())["data"][0]["embedding"]
        self.cache[text] = vector
        return vector


def score_run(
    scenario: dict[str, Any],
    sections: list[str],
    *,
    profile: str,
    backend: str,
    top_k: int,
    latency_ms: float,
) -> dict[str, Any]:
    expected = set(scenario["expected"])
    retrieved = set(sections)
    relevant = expected & retrieved
    first_rank = next((index for index, section in enumerate(sections, start=1) if section in expected), None)
    return {
        "scenario_id": scenario["id"],
        "title": scenario["title"],
        "question": scenario["question"],
        "expected": scenario["expected"],
        "profile": profile,
        "backend": backend,
        "top_k": top_k,
        "sections": sections,
        "recall": round(len(relevant) / len(expected), 4),
        "precision": round(len(relevant) / max(1, len(sections)), 4),
        "all_expected_found": expected <= retrieved,
        "reciprocal_rank": round(1 / first_rank, 4) if first_rank else 0.0,
        "latency_ms": round(latency_ms, 2),
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "runs": len(rows),
        "macro_recall": round(statistics.mean(row["recall"] for row in rows), 4),
        "macro_precision": round(statistics.mean(row["precision"] for row in rows), 4),
        "mrr": round(statistics.mean(row["reciprocal_rank"] for row in rows), 4),
        "all_expected_rate": round(statistics.mean(float(row["all_expected_found"]) for row in rows), 4),
        "mean_latency_ms": round(statistics.mean(row["latency_ms"] for row in rows), 2),
        "p95_latency_ms": round(sorted(row["latency_ms"] for row in rows)[max(0, int(len(rows) * 0.95) - 1)], 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=ROOT / "rag_webui_8083/data/ncb_nitibench_hybrid_corpus.json")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--embedding-endpoint", default="http://127.0.0.1:8082/v1/embeddings")
    parser.add_argument("--embedding-model", default="Qwen3-Embedding-4B")
    parser.add_argument("--qdrant-path", type=Path, default=ROOT / "rag_webui_8083/data/qdrant_local")
    args = parser.parse_args()

    records = json.loads(args.corpus.read_text(encoding="utf-8"))
    scenarios = load_ncb_scenarios()
    embed = EmbeddingClient(args.embedding_endpoint, args.embedding_model)
    memory = MemoryDenseBackend(records)
    memory_engine = LegalHybridRetriever(records, embed_query=embed, dense_backend=memory)

    profile_specs = [
        ("bm25", 0.55),
        ("fts5", 0.55),
        ("dense", 0.55),
        ("weighted_hybrid_035", 0.35),
        ("weighted_hybrid_055", 0.55),
        ("weighted_hybrid_075", 0.75),
        ("rrf_hybrid", 0.55),
        ("adaptive_hybrid", 0.55),
        ("legal_advanced", 0.55),
    ]
    all_runs: list[dict[str, Any]] = []
    summaries: dict[str, dict[str, Any]] = {}
    for top_k in (4, 6, 8, 12):
        for label, weight in profile_specs:
            profile = "weighted_hybrid" if label.startswith("weighted_hybrid") else label
            group = []
            for scenario in scenarios:
                started = time.perf_counter()
                hits = memory_engine.search(
                    scenario["question"],
                    profile=profile,
                    top_k=top_k,
                    candidate_k=36,
                    dense_weight=weight,
                )
                latency = (time.perf_counter() - started) * 1000
                sections = [
                    section_number(hit.record.get("section") or hit.record.get("clause"))
                    for hit in hits
                ]
                row = score_run(
                    scenario,
                    sections,
                    profile=label,
                    backend=memory.name,
                    top_k=top_k,
                    latency_ms=latency,
                )
                all_runs.append(row)
                group.append(row)
            summaries[f"{memory.name}:{label}:k{top_k}"] = aggregate(group)

    qdrant = QdrantDenseBackend(
        records,
        collection="ncb_structural_v1",
        local_path=args.qdrant_path,
        recreate=False,
    )
    qdrant_engine = LegalHybridRetriever(records, embed_query=embed, dense_backend=qdrant)
    for profile in ("dense", "rrf_hybrid", "legal_advanced"):
        group = []
        for scenario in scenarios:
            started = time.perf_counter()
            hits = qdrant_engine.search(scenario["question"], profile=profile, top_k=8, candidate_k=36)
            latency = (time.perf_counter() - started) * 1000
            sections = [
                section_number(hit.record.get("section") or hit.record.get("clause"))
                for hit in hits
            ]
            row = score_run(
                scenario,
                sections,
                profile=profile,
                backend=qdrant.name,
                top_k=8,
                latency_ms=latency,
            )
            all_runs.append(row)
            group.append(row)
        summaries[f"{qdrant.name}:{profile}:k8"] = aggregate(group)

    output = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "corpus": str(args.corpus),
        "corpus_size": len(records),
        "scenarios": len(scenarios),
        "embedding_model": args.embedding_model,
        "summaries": summaries,
        "runs": all_runs,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    best = sorted(
        summaries.items(),
        key=lambda item: (
            item[1]["macro_recall"],
            item[1]["all_expected_rate"],
            item[1]["mrr"],
            item[1]["macro_precision"],
        ),
        reverse=True,
    )[:10]
    print(json.dumps({"best": best}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
