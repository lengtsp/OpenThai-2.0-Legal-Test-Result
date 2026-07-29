#!/usr/bin/env python3
"""Index the same legal corpus in Qdrant, Chroma, and Milvus Lite."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "rag_webui_8083"))

from legal_retrieval import (  # noqa: E402
    ChromaDenseBackend,
    MilvusDenseBackend,
    QdrantDenseBackend,
    section_number,
)


def embed(text: str) -> list[float]:
    payload = json.dumps({"model": "Qwen3-Embedding-4B", "input": text}, ensure_ascii=False).encode()
    request = urllib.request.Request(
        "http://127.0.0.1:8082/v1/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode())["data"][0]["embedding"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--corpus",
        type=Path,
        default=ROOT / "rag_webui_8083/data/ncb_nitibench_hybrid_corpus.json",
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.data_root.mkdir(parents=True, exist_ok=True)
    records = json.loads(args.corpus.read_text(encoding="utf-8"))
    question = "ธนาคารปฏิเสธสินเชื่อเพราะข้อมูลเครดิต ต้องแจ้งลูกค้าและให้สิทธิตรวจสอบอย่างไร"
    vector = embed(question)
    factories = {
        "qdrant_local": lambda: QdrantDenseBackend(
            records,
            collection="ncb_backend_smoke",
            local_path=args.data_root / "qdrant",
            recreate=True,
        ),
        "chroma_persistent": lambda: ChromaDenseBackend(
            records,
            collection="ncb_backend_smoke",
            local_path=args.data_root / "chroma",
        ),
        "milvus_lite": lambda: MilvusDenseBackend(
            records,
            collection="ncb_backend_smoke",
            uri=str(args.data_root / "milvus.db"),
            recreate=True,
        ),
    }
    results = []
    for name, factory in factories.items():
        started = time.perf_counter()
        try:
            backend = factory()
            indexed_ms = (time.perf_counter() - started) * 1000
            search_started = time.perf_counter()
            hits = backend.search(vector, 8)
            results.append(
                {
                    "backend": name,
                    "status": "passed",
                    "records": len(records),
                    "index_ms": round(indexed_ms, 2),
                    "search_ms": round((time.perf_counter() - search_started) * 1000, 2),
                    "sections": [
                        section_number(hit.record.get("section") or hit.record.get("clause"))
                        for hit in hits
                    ],
                }
            )
        except Exception as exc:
            results.append(
                {
                    "backend": name,
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"question": question, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if any(row["status"] != "passed" for row in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
