"""Backend-neutral legal retrieval for Thai structural chunks.

The module deliberately separates four concerns:

* lexical ranking (Python BM25 or SQLite FTS5 trigram);
* dense-vector storage (memory, Qdrant, Chroma, or Milvus);
* fusion (weighted score or reciprocal-rank fusion);
* legal structure (Thai numeral normalization and linked-penalty expansion).

Every backend returns the same record contract, so retrieval quality can be
benchmarked independently from OpenThai answer generation.
"""

from __future__ import annotations

import math
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

import numpy as np


THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
SANCTION_TERMS = (
    "โทษ", "บทลงโทษ", "ระวาง", "ความผิด", "ผิดกฎหมาย",
    "ผลตามกฎหมาย", "ผลทางกฎหมาย", "ความรับผิด", "จำคุก", "ปรับ",
)


def tokens(text: str) -> list[str]:
    """Thai-friendly words plus character trigrams."""
    normalized = re.sub(r"\s+", " ", text.lower()).strip()
    words = re.findall(r"[\u0e00-\u0e7fa-z0-9/]+", normalized)
    joined = re.sub(r"[^\u0e00-\u0e7fa-z0-9/]", "", normalized)
    grams = [joined[index : index + 3] for index in range(max(0, len(joined) - 2))]
    return words + grams


def expanded_legal_query(query: str) -> str:
    """Map common operational wording to statutory vocabulary."""
    lower = query.lower()
    additions: list[str] = []
    if any(term in lower for term in ("แคป", "แชต", "ไลน์", "line", "กลุ่ม", "รั่ว", "เปิดเผย", "เผยแพร่")):
        additions.append("เปิดเผยหรือเผยแพร่ข้อมูลแก่ผู้อื่นที่ไม่มีสิทธิรับรู้ เก็บรักษาข้อมูลเป็นความลับ")
    if any(term in lower for term in ("พนักงาน", "เจ้าหน้าที่", "ผู้ปฏิบัติงาน", "ปฏิบัติหน้าที่")):
        additions.append("ผู้ซึ่งรู้ข้อมูลจากการทำงานหรือปฏิบัติหน้าที่ ห้ามเปิดเผยข้อมูล")
    if any(term in lower for term in ("ยินยอม", "consent", "ดึงข้อมูล", "ทบทวนวงเงิน", "annual review")):
        additions.append("ได้รับความยินยอมจากเจ้าของข้อมูลก่อนเปิดเผยหรือให้ข้อมูลเพื่อวิเคราะห์สินเชื่อ")
    if any(term in lower for term in ("การตลาด", "ตลาด", "cross-selling", "ประกัน")):
        additions.append("ใช้ข้อมูลตามวัตถุประสงค์ที่กำหนด ห้ามใช้หรือเปิดเผยแก่ผู้ไม่มีสิทธิรับรู้")
    if any(term in lower for term in ("ปฏิเสธสินเชื่อ", "ไม่อนุมัติ", "ไม่ผ่าน")):
        additions.append("แสดงเหตุผลและแหล่งที่มาของข้อมูลเป็นหนังสือ สิทธิตรวจสอบข้อมูลโดยไม่เสียค่าธรรมเนียม")
    if any(term in lower for term in ("ข้อมูลผิด", "ผิดพลาด", "แก้ไข", "ค้างชำระ")):
        additions.append("ส่งข้อมูลที่ถูกต้องและทันสมัย ตรวจสอบแก้ไขและแจ้งผลภายในสามสิบวัน")
    if any(term in lower for term in ("เครดิตสกอร์", "credit score", "credit model", "แบบจำลอง")):
        additions.append("ข้อมูลคะแนนเครดิต แบบจำลองด้านเครดิต ความยินยอมเป็นการเฉพาะ")
    return f"{query}\nคำค้นตามถ้อยคำกฎหมาย: {' ; '.join(additions)}" if additions else query


def section_number(value: object) -> str:
    normalized = str(value or "").translate(THAI_DIGITS)
    match = re.search(r"มาตรา\s*([0-9]+(?:\s*/\s*[0-9]+)?)", normalized)
    if match:
        return re.sub(r"\s+", "", match.group(1))
    match = re.fullmatch(r"\s*([0-9]+(?:\s*/\s*[0-9]+)?)\s*", normalized)
    return re.sub(r"\s+", "", match.group(1)) if match else ""


def referenced_sections(content: object) -> set[str]:
    normalized = str(content or "").translate(THAI_DIGITS)
    return {
        re.sub(r"\s+", "", match)
        for match in re.findall(r"มาตรา\s*([0-9]+(?:\s*/\s*[0-9]+)?)", normalized)
    }


def record_id(record: dict[str, Any]) -> str:
    return str(record.get("id") or f"{record.get('law_name', '')}:{record.get('section', '')}")


def searchable_text(record: dict[str, Any]) -> str:
    return " ".join(
        str(record.get(key, ""))
        for key in ("law_name", "instrument", "topic", "section", "clause", "content")
    )


def _normalized(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    low, high = min(values.values()), max(values.values())
    if math.isclose(low, high):
        return {key: 1.0 for key in values}
    return {key: (value - low) / (high - low) for key, value in values.items()}


@dataclass(frozen=True)
class SearchHit:
    record: dict[str, Any]
    score: float
    lexical_score: float = 0.0
    dense_score: float = 0.0
    fts_score: float = 0.0
    source: str = ""


class DenseBackend(Protocol):
    name: str

    def search(self, vector: list[float], top_k: int) -> list[SearchHit]:
        ...


class PythonBM25Index:
    name = "python_bm25"

    def __init__(self, records: list[dict[str, Any]]) -> None:
        self.records = records
        self.doc_terms = [tokens(searchable_text(record)) for record in records]
        self.df = Counter(term for terms in self.doc_terms for term in set(terms))
        self.average_length = max(1.0, sum(map(len, self.doc_terms)) / max(1, len(self.doc_terms)))

    def search(self, query: str, top_k: int) -> list[SearchHit]:
        query_terms = set(tokens(query))
        total = len(self.records)
        ranked: list[SearchHit] = []
        for record, terms in zip(self.records, self.doc_terms):
            counts = Counter(terms)
            score = 0.0
            for term in query_terms:
                frequency = counts.get(term, 0)
                if not frequency:
                    continue
                idf = math.log(1 + (total - self.df[term] + 0.5) / (self.df[term] + 0.5))
                score += idf * (frequency * 2.2) / (
                    frequency + 1.2 * (1 - 0.75 + 0.75 * len(terms) / self.average_length)
                )
            if score > 0:
                ranked.append(SearchHit(record, score, lexical_score=score, source=self.name))
        ranked.sort(key=lambda hit: hit.score, reverse=True)
        return ranked[: max(1, top_k)]


class SQLiteFTS5Index:
    """SQLite FTS5 BM25 with trigram tokenization for unsegmented Thai text."""

    name = "sqlite_fts5_trigram"

    def __init__(self, records: list[dict[str, Any]], path: str | Path = ":memory:") -> None:
        self.records = {record_id(record): record for record in records}
        self.connection = sqlite3.connect(str(path))
        self.connection.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS legal_fts USING fts5(id UNINDEXED, body, tokenize='trigram')"
        )
        self.connection.execute("DELETE FROM legal_fts")
        self.connection.executemany(
            "INSERT INTO legal_fts(id, body) VALUES (?, ?)",
            [(record_id(record), searchable_text(record)) for record in records],
        )
        self.connection.commit()

    @staticmethod
    def _query(value: str) -> str:
        unique: list[str] = []
        for term in tokens(value):
            if len(term) < 3 or term in unique:
                continue
            unique.append(term.replace('"', '""'))
            if len(unique) >= 72:
                break
        return " OR ".join(f'"{term}"' for term in unique)

    def search(self, query: str, top_k: int) -> list[SearchHit]:
        expression = self._query(query)
        if not expression:
            return []
        rows = self.connection.execute(
            "SELECT id, bm25(legal_fts, 0.0, 1.0) AS rank "
            "FROM legal_fts WHERE legal_fts MATCH ? ORDER BY rank LIMIT ?",
            (expression, max(1, top_k)),
        ).fetchall()
        return [
            SearchHit(self.records[row_id], -float(rank), fts_score=-float(rank), source=self.name)
            for row_id, rank in rows
            if row_id in self.records
        ]


class MemoryDenseBackend:
    name = "memory_dense"

    def __init__(self, records: list[dict[str, Any]]) -> None:
        self.records: list[dict[str, Any]] = []
        vectors: list[np.ndarray] = []
        for record in records:
            raw = record.get("embedding") or record.get("vector") or []
            vector = np.asarray(raw, dtype=np.float32)
            if vector.size:
                self.records.append(record)
                vectors.append(vector)
        self.matrix = np.vstack(vectors) if vectors else np.empty((0, 0), dtype=np.float32)
        if vectors:
            self.matrix /= np.maximum(np.linalg.norm(self.matrix, axis=1)[:, None], 1e-12)

    def search(self, vector: list[float], top_k: int) -> list[SearchHit]:
        if not self.records:
            return []
        query = np.asarray(vector, dtype=np.float32)
        if query.size != self.matrix.shape[1]:
            raise ValueError(f"embedding dimension mismatch: query={query.size}, index={self.matrix.shape[1]}")
        query /= max(float(np.linalg.norm(query)), 1e-12)
        scores = self.matrix @ query
        limit = min(max(1, top_k), len(self.records))
        indices = np.argpartition(-scores, limit - 1)[:limit]
        indices = indices[np.argsort(-scores[indices])]
        return [
            SearchHit(self.records[int(index)], float(scores[int(index)]), dense_score=float(scores[int(index)]), source=self.name)
            for index in indices
        ]


class QdrantDenseBackend:
    """Qdrant adapter supporting a URL or embedded local storage."""

    name = "qdrant_dense"

    def __init__(
        self,
        records: list[dict[str, Any]],
        *,
        collection: str = "openthai_legal",
        url: str | None = None,
        local_path: str | Path | None = None,
        recreate: bool = False,
    ) -> None:
        from qdrant_client import QdrantClient, models

        if not records:
            raise ValueError("cannot build Qdrant collection from an empty corpus")
        vector_size = len(records[0].get("embedding") or records[0].get("vector") or [])
        if not vector_size:
            raise ValueError("Qdrant records do not contain embeddings")
        self.models = models
        self.collection = collection
        self.client = QdrantClient(url=url) if url else QdrantClient(path=str(local_path or ":memory:"))
        existing = {item.name for item in self.client.get_collections().collections}
        if recreate and collection in existing:
            self.client.delete_collection(collection)
            existing.remove(collection)
        if collection not in existing:
            self.client.create_collection(
                collection_name=collection,
                vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
            )
        points = []
        for index, record in enumerate(records, start=1):
            vector = record.get("embedding") or record.get("vector") or []
            payload = {
                "record_id": record_id(record),
                "law_name": str(record.get("law_name") or record.get("instrument") or ""),
                "section": str(record.get("section") or record.get("clause") or ""),
                "topic": str(record.get("topic") or ""),
                "content": str(record.get("content") or ""),
                "page_start": record.get("page_start"),
                "page_end": record.get("page_end"),
                "source_url": str(record.get("source_url") or ""),
            }
            points.append(models.PointStruct(id=index, vector=vector, payload=payload))
        for start in range(0, len(points), 64):
            self.client.upsert(collection_name=collection, points=points[start : start + 64], wait=True)

    @staticmethod
    def _record(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": payload.get("record_id"),
            "law_name": payload.get("law_name"),
            "instrument": payload.get("law_name"),
            "section": payload.get("section"),
            "clause": payload.get("section"),
            "topic": payload.get("topic"),
            "content": payload.get("content"),
            "page_start": payload.get("page_start"),
            "page_end": payload.get("page_end"),
            "source_url": payload.get("source_url"),
        }

    def search(self, vector: list[float], top_k: int) -> list[SearchHit]:
        response = self.client.query_points(
            collection_name=self.collection,
            query=vector,
            limit=max(1, top_k),
            with_payload=True,
        )
        return [
            SearchHit(self._record(point.payload or {}), float(point.score), dense_score=float(point.score), source=self.name)
            for point in response.points
        ]


class ChromaDenseBackend:
    """Chroma adapter; dependencies are imported only when selected."""

    name = "chroma_dense"

    def __init__(
        self,
        records: list[dict[str, Any]],
        *,
        collection: str = "openthai_legal",
        local_path: str | Path | None = None,
        host: str | None = None,
        port: int = 8000,
    ) -> None:
        import chromadb

        client = (
            chromadb.HttpClient(host=host, port=port)
            if host
            else chromadb.PersistentClient(path=str(local_path or ".chroma"))
        )
        self.collection = client.get_or_create_collection(collection, metadata={"hnsw:space": "cosine"})
        ids = [record_id(record) for record in records]
        self.collection.upsert(
            ids=ids,
            embeddings=[record.get("embedding") or record.get("vector") for record in records],
            documents=[str(record.get("content") or "") for record in records],
            metadatas=[
                {
                    "law_name": str(record.get("law_name") or record.get("instrument") or ""),
                    "section": str(record.get("section") or record.get("clause") or ""),
                    "topic": str(record.get("topic") or ""),
                    "page_start": int(record.get("page_start") or 0),
                    "page_end": int(record.get("page_end") or 0),
                    "source_url": str(record.get("source_url") or ""),
                }
                for record in records
            ],
        )

    def search(self, vector: list[float], top_k: int) -> list[SearchHit]:
        result = self.collection.query(query_embeddings=[vector], n_results=max(1, top_k))
        output: list[SearchHit] = []
        for item_id, document, metadata, distance in zip(
            result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0]
        ):
            record = {"id": item_id, "content": document, **metadata}
            score = 1.0 - float(distance)
            output.append(SearchHit(record, score, dense_score=score, source=self.name))
        return output


class MilvusDenseBackend:
    """Milvus/Milvus Lite adapter; dependencies are imported only when selected."""

    name = "milvus_dense"

    def __init__(
        self,
        records: list[dict[str, Any]],
        *,
        collection: str = "openthai_legal",
        uri: str = "./milvus_legal.db",
        recreate: bool = False,
    ) -> None:
        from pymilvus import DataType, MilvusClient

        if not records:
            raise ValueError("cannot build Milvus collection from an empty corpus")
        dimension = len(records[0].get("embedding") or records[0].get("vector") or [])
        self.client = MilvusClient(uri=uri)
        self.collection = collection
        if recreate and self.client.has_collection(collection):
            self.client.drop_collection(collection)
        if not self.client.has_collection(collection):
            schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
            schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=256)
            schema.add_field("vector", DataType.FLOAT_VECTOR, dim=dimension)
            index = self.client.prepare_index_params()
            index.add_index("vector", index_type="AUTOINDEX", metric_type="COSINE")
            self.client.create_collection(collection, schema=schema, index_params=index)
        data = []
        for record in records:
            data.append(
                {
                    "id": record_id(record),
                    "vector": record.get("embedding") or record.get("vector"),
                    "law_name": str(record.get("law_name") or record.get("instrument") or ""),
                    "section": str(record.get("section") or record.get("clause") or ""),
                    "topic": str(record.get("topic") or ""),
                    "content": str(record.get("content") or ""),
                    "page_start": int(record.get("page_start") or 0),
                    "page_end": int(record.get("page_end") or 0),
                    "source_url": str(record.get("source_url") or ""),
                }
            )
        self.client.upsert(collection, data)

    def search(self, vector: list[float], top_k: int) -> list[SearchHit]:
        response = self.client.search(
            collection_name=self.collection,
            data=[vector],
            anns_field="vector",
            limit=max(1, top_k),
            output_fields=["law_name", "section", "topic", "content", "page_start", "page_end", "source_url"],
            search_params={"metric_type": "COSINE"},
        )[0]
        output = []
        for hit in response:
            entity = dict(hit.get("entity") or {})
            entity["id"] = hit.get("id")
            score = float(hit.get("distance") or 0.0)
            output.append(SearchHit(entity, score, dense_score=score, source=self.name))
        return output


class LegalHybridRetriever:
    """Profile-driven retrieval with interchangeable dense storage."""

    PROFILES = (
        "bm25",
        "fts5",
        "dense",
        "weighted_hybrid",
        "rrf_hybrid",
        "adaptive_hybrid",
        "legal_advanced",
    )

    def __init__(
        self,
        records: list[dict[str, Any]],
        *,
        embed_query: Callable[[str], list[float]],
        dense_backend: DenseBackend | None = None,
        fts_path: str | Path = ":memory:",
    ) -> None:
        self.records = records
        self.embed_query = embed_query
        self.bm25 = PythonBM25Index(records)
        self.fts5 = SQLiteFTS5Index(records, fts_path)
        self.dense = dense_backend or MemoryDenseBackend(records)
        self.by_id = {record_id(record): record for record in records}

    @staticmethod
    def _rrf(rankings: list[list[SearchHit]], *, rrf_k: int = 60) -> list[SearchHit]:
        fused: dict[str, float] = {}
        records: dict[str, dict[str, Any]] = {}
        components: dict[str, dict[str, float]] = {}
        for ranking in rankings:
            for rank, hit in enumerate(ranking, start=1):
                identifier = record_id(hit.record)
                records[identifier] = hit.record
                fused[identifier] = fused.get(identifier, 0.0) + 1.0 / (rrf_k + rank)
                component = components.setdefault(identifier, {"lexical": 0.0, "dense": 0.0, "fts": 0.0})
                component["lexical"] = max(component["lexical"], hit.lexical_score)
                component["dense"] = max(component["dense"], hit.dense_score)
                component["fts"] = max(component["fts"], hit.fts_score)
        ordered = sorted(fused, key=fused.get, reverse=True)
        return [
            SearchHit(
                records[identifier],
                fused[identifier],
                lexical_score=components[identifier]["lexical"],
                dense_score=components[identifier]["dense"],
                fts_score=components[identifier]["fts"],
                source="rrf",
            )
            for identifier in ordered
        ]

    @staticmethod
    def _weighted(lexical: list[SearchHit], dense: list[SearchHit], alpha: float) -> list[SearchHit]:
        lexical_raw = {record_id(hit.record): hit.score for hit in lexical}
        dense_raw = {record_id(hit.record): hit.score for hit in dense}
        lexical_norm, dense_norm = _normalized(lexical_raw), _normalized(dense_raw)
        records = {record_id(hit.record): hit.record for hit in lexical + dense}
        identifiers = set(lexical_norm) | set(dense_norm)
        output = [
            SearchHit(
                records[identifier],
                alpha * dense_norm.get(identifier, 0.0) + (1 - alpha) * lexical_norm.get(identifier, 0.0),
                lexical_score=lexical_raw.get(identifier, 0.0),
                dense_score=dense_raw.get(identifier, 0.0),
                source=f"weighted_{alpha:.2f}",
            )
            for identifier in identifiers
        ]
        output.sort(key=lambda hit: hit.score, reverse=True)
        return output

    @staticmethod
    def _dedupe(hits: list[SearchHit]) -> list[SearchHit]:
        output: list[SearchHit] = []
        seen: set[tuple[str, str]] = set()
        for hit in hits:
            key = (
                str(hit.record.get("law_name") or hit.record.get("instrument") or ""),
                section_number(hit.record.get("section") or hit.record.get("clause")),
            )
            if key in seen:
                continue
            seen.add(key)
            output.append(hit)
        return output

    @staticmethod
    def _interleave(rankings: list[tuple[list[SearchHit], int]]) -> list[SearchHit]:
        """Build a quota-preserving candidate union without score calibration.

        Thai legal queries often contain both a semantic fact pattern and exact
        statutory vocabulary.  RRF is useful for a final ordering, but it can
        push a dense-only provision out of a bounded candidate pool.  This
        weighted round-robin keeps every channel represented before an LLM
        reranker reads the candidates.
        """
        output: list[SearchHit] = []
        offsets = [0 for _ in rankings]
        while True:
            added = False
            for ranking_index, (ranking, quota) in enumerate(rankings):
                for _ in range(quota):
                    if offsets[ranking_index] >= len(ranking):
                        break
                    output.append(ranking[offsets[ranking_index]])
                    offsets[ranking_index] += 1
                    added = True
            if not added:
                break
        return output

    @staticmethod
    def _role_aware(query: str, hits: list[SearchHit]) -> list[SearchHit]:
        """Boost provisions whose actor wording matches the scenario."""
        lower = query.lower()
        employee_actor = any(term in lower for term in ("พนักงาน", "เจ้าหน้าที่", "ผู้ปฏิบัติงาน", "ปฏิบัติหน้าที่"))
        if not employee_actor:
            return hits
        promoted: list[SearchHit] = []
        remaining: list[SearchHit] = []
        for hit in hits:
            content = str(hit.record.get("content") or "")
            target = promoted if (
                "ผู้ซึ่งรู้ข้อมูลจากการทำงาน" in content
                or "ผู้ซึ่งรู้ข้อมูลจากการปฏิบัติหน้าที่" in content
            ) else remaining
            target.append(hit)
        # Stable partitioning preserves the quota-balanced cross-channel order;
        # raw BM25, FTS and cosine scores are deliberately not compared.
        return promoted + remaining

    def _linked_penalties(self, query: str, hits: list[SearchHit], maximum: int = 8) -> list[SearchHit]:
        if not any(term in query for term in SANCTION_TERMS):
            return hits
        penalties: dict[str, list[dict[str, Any]]] = {}
        for record in self.records:
            content = str(record.get("content") or "")
            if "ต้องระวางโทษ" not in content:
                continue
            for referenced in referenced_sections(content):
                penalties.setdefault(referenced, []).append(record)
        output: list[SearchHit] = []
        present: set[str] = set()
        additions = 0
        for hit in hits:
            identifier = record_id(hit.record)
            if identifier in present:
                continue
            output.append(hit)
            present.add(identifier)
            content = str(hit.record.get("content") or "")
            if "ต้องระวางโทษ" in content or additions >= maximum:
                continue
            section = section_number(hit.record.get("section") or hit.record.get("clause"))
            for penalty in penalties.get(section, []):
                penalty_id = record_id(penalty)
                if penalty_id in present:
                    continue
                output.append(SearchHit(penalty, hit.score * 0.999, source="linked_penalty"))
                present.add(penalty_id)
                additions += 1
                if additions >= maximum:
                    break
        return output

    def search(
        self,
        query: str,
        *,
        profile: str = "legal_advanced",
        top_k: int = 8,
        candidate_k: int = 36,
        dense_weight: float = 0.55,
    ) -> list[SearchHit]:
        if profile not in self.PROFILES:
            raise ValueError(f"unknown retrieval profile {profile!r}; choose from {self.PROFILES}")
        search_query = expanded_legal_query(query) if profile in {"adaptive_hybrid", "legal_advanced"} else query
        needs_dense = profile not in {"bm25", "fts5"}
        # Embed the original fact pattern. Query expansion is valuable for
        # lexical matching but can dilute the semantic vector with generic
        # legal vocabulary.
        vector = self.embed_query(query) if needs_dense else []
        needs_lexical = profile not in {"dense", "fts5"}
        needs_fts = profile in {"fts5", "adaptive_hybrid", "legal_advanced"}
        lexical = self.bm25.search(search_query, candidate_k) if needs_lexical else []
        fts = self.fts5.search(search_query, candidate_k) if needs_fts else []
        dense = self.dense.search(vector, candidate_k) if needs_dense else []

        if profile == "bm25":
            ranked = lexical
        elif profile == "fts5":
            ranked = fts
        elif profile == "dense":
            ranked = dense
        elif profile == "weighted_hybrid":
            ranked = self._weighted(lexical, dense, dense_weight)
        elif profile == "rrf_hybrid":
            ranked = self._rrf([lexical, dense])
        elif profile == "adaptive_hybrid":
            has_exact_section = bool(re.search(r"มาตรา\s*[๐-๙0-9]+", query))
            alpha = 0.35 if has_exact_section else 0.6
            ranked = self._weighted(self._rrf([lexical, fts]), dense, alpha)
        else:
            # Reserve two dense positions for every lexical and FTS position.
            # The pool remains genuinely hybrid, while semantic provisions
            # that occur in only one channel cannot be eliminated by fusion.
            ranked = self._interleave([(dense, 2), (lexical, 1), (fts, 1)])
            ranked = self._role_aware(query, ranked)
            ranked = self._linked_penalties(query, ranked)

        return self._dedupe(ranked)[: max(1, top_k)]
