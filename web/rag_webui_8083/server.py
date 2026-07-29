#!/usr/bin/env python3
"""Legal RAG workbench, backed by a local OpenAI-compatible API.

The service deliberately keeps the corpus lightweight and inspectable: every
retrieved item has a source title and section, and the exact chunk that was
given to the model is returned to the browser as citation evidence.
"""

from __future__ import annotations

import json
import math
import os
import re
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections import Counter
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import psycopg2
from psycopg2.extras import Json, RealDictCursor

from legal_retrieval import (
    ChromaDenseBackend,
    LegalHybridRetriever,
    MemoryDenseBackend,
    MilvusDenseBackend,
    QdrantDenseBackend,
    referenced_sections as legal_referenced_sections,
)


ROOT = Path(__file__).resolve().parent
CORPUS_PATH = Path(os.getenv("RAG_CORPUS_PATH", ROOT / "data" / "legal_corpus.json"))
VLLM_URL = os.getenv("RAG_LLM_URL", "http://127.0.0.1:3033/v1/chat/completions")
VLLM_MODELS_URL = os.getenv("RAG_LLM_MODELS_URL", "http://127.0.0.1:3033/v1/models")
MODEL_NAME = os.getenv("RAG_LLM_MODEL", "iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b")
EMBEDDING_URL = os.getenv("RAG_EMBEDDING_URL", "http://127.0.0.1:8082/v1/embeddings")
EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "Qwen3-Embedding-4B")
HYBRID_CANDIDATE_K = max(24, min(int(os.getenv("RAG_HYBRID_CANDIDATE_K", "32")), 60))
# This is an evidence-identification pass, not the final answer context. A
# bounded excerpt keeps 32 candidates safely inside the model context window.
RERANK_CONTEXT_CHARS = max(450, min(int(os.getenv("RAG_RERANK_CONTEXT_CHARS", "1200")), 2000))
EVIDENCE_CHAR_BUDGET = max(8_000, min(int(os.getenv("RAG_EVIDENCE_CHAR_BUDGET", "18000")), 40_000))
ANSWER_EVIDENCE_K = max(2, min(int(os.getenv("RAG_ANSWER_EVIDENCE_K", "6")), 6))
RETRIEVAL_PROFILE = os.getenv("RAG_RETRIEVAL_PROFILE", "legal_advanced").strip()
VECTOR_BACKEND = os.getenv("RAG_VECTOR_BACKEND", "memory").strip().lower()
_RETRIEVER_CACHE: dict[str, Any] = {}
_RETRIEVER_LOCK = threading.RLock()


def _db_connection():
    """Open a short-lived PostgreSQL connection for one HTTP request."""
    user = os.getenv("OPENGPT_DB_USER", "").strip()
    password = os.getenv("OPENGPT_DB_PASSWORD", "")
    if not user or not password:
        raise RuntimeError("PostgreSQL session storage is not configured")
    return psycopg2.connect(
        host=os.getenv("OPENGPT_DB_HOST", "127.0.0.1"),
        port=int(os.getenv("OPENGPT_DB_PORT", "5432")),
        dbname=os.getenv("OPENGPT_DB_NAME", "opengpt"),
        user=user,
        password=password,
        connect_timeout=5,
    )


def _session_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def create_session(title: str = "") -> dict[str, Any]:
    session_id = uuid.uuid4()
    clean_title = (title.strip() or "New legal chat")[:160]
    with _db_connection() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            "INSERT INTO chat_sessions (id, title) VALUES (%s, %s) RETURNING id, title, created_at, updated_at",
            (str(session_id), clean_title),
        )
        return _session_payload(cursor.fetchone())


def get_session(session_id: str) -> dict[str, Any] | None:
    try:
        parsed_id = str(uuid.UUID(session_id))
    except (ValueError, TypeError, AttributeError):
        return None
    with _db_connection() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT id, title, created_at, updated_at FROM chat_sessions WHERE id = %s", (parsed_id,))
        row = cursor.fetchone()
        if not row:
            return None
        session = _session_payload(row)
        cursor.execute(
            "SELECT id, role, content, reasoning, citations, usage, timing, created_at FROM chat_messages WHERE session_id = %s ORDER BY id",
            (parsed_id,),
        )
        session["messages"] = [
            {
                "id": message["id"], "role": message["role"], "content": message["content"],
                "reasoning": message["reasoning"], "citations": message["citations"],
                "usage": message["usage"], "timing": message["timing"], "created_at": message["created_at"].isoformat(),
            }
            for message in cursor.fetchall()
        ]
        return session


def list_sessions(limit: int = 20) -> list[dict[str, Any]]:
    with _db_connection() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            "SELECT id, title, created_at, updated_at FROM chat_sessions ORDER BY updated_at DESC LIMIT %s",
            (max(1, min(limit, 100)),),
        )
        return [_session_payload(row) for row in cursor.fetchall()]


def _history_for_model(session_id: str) -> list[dict[str, str]]:
    with _db_connection() as connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            "SELECT role, content FROM chat_messages WHERE session_id = %s ORDER BY id DESC LIMIT 6",
            (session_id,),
        )
        rows = list(reversed(cursor.fetchall()))
        return [{"role": row["role"], "content": row["content"]} for row in rows]


def _save_message(session_id: str, role: str, content: str, *, reasoning: str = "", citations: list[dict[str, Any]] | None = None, usage: dict[str, Any] | None = None, timing: dict[str, Any] | None = None) -> None:
    with _db_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO chat_messages (session_id, role, content, reasoning, citations, usage, timing)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (session_id, role, content, reasoning, Json(citations or []), Json(usage or {}), Json(timing or {})),
        )
        cursor.execute("UPDATE chat_sessions SET updated_at = now() WHERE id = %s", (session_id,))


def _resolve_session(value: object, title: str) -> dict[str, Any]:
    if value:
        existing = get_session(str(value))
        if not existing:
            raise ValueError("ไม่พบ session ที่ร้องขอ โปรดเริ่มแชตใหม่")
        return existing
    return create_session(title)


def _read_corpus() -> list[dict[str, str]]:
    try:
        payload = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else []
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError):
        return []


def _write_corpus(items: list[dict[str, str]]) -> None:
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = CORPUS_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(CORPUS_PATH)


def _tokens(text: str) -> list[str]:
    """Word tokens plus Thai-friendly character trigrams for robust lexical RAG."""
    normalized = re.sub(r"\s+", " ", text.lower()).strip()
    words = re.findall(r"[\u0e00-\u0e7fa-z0-9]+", normalized)
    joined = re.sub(r"[^\u0e00-\u0e7fa-z0-9]", "", normalized)
    grams = [joined[i : i + 3] for i in range(max(0, len(joined) - 2))]
    return words + grams


def _embed_query(query: str) -> list[float]:
    payload = _request_json(EMBEDDING_URL, {"model": EMBEDDING_MODEL, "input": query}, timeout=30)
    data = payload.get("data") or []
    return list(data[0].get("embedding") or []) if data else []


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


def _retriever() -> LegalHybridRetriever:
    """Build and cache the selected retrieval backend for the active corpus."""
    try:
        signature = f"{CORPUS_PATH.resolve()}:{CORPUS_PATH.stat().st_mtime_ns}:{VECTOR_BACKEND}"
    except FileNotFoundError:
        signature = f"{CORPUS_PATH.resolve()}:missing:{VECTOR_BACKEND}"
    cached = _RETRIEVER_CACHE.get(signature)
    if cached:
        return cached
    with _RETRIEVER_LOCK:
        cached = _RETRIEVER_CACHE.get(signature)
        if cached:
            return cached
        return _build_retriever(signature)


def _build_retriever(signature: str) -> LegalHybridRetriever:
    """Create one backend instance while the caller holds the init lock."""
    records = _read_corpus()
    if VECTOR_BACKEND == "qdrant":
        dense = QdrantDenseBackend(
            records,
            collection=os.getenv("RAG_QDRANT_COLLECTION", "openthai_legal"),
            url=os.getenv("RAG_QDRANT_URL") or None,
            local_path=os.getenv("RAG_QDRANT_PATH", str(ROOT / "data" / "qdrant_local")),
            recreate=False,
        )
    elif VECTOR_BACKEND == "chroma":
        dense = ChromaDenseBackend(
            records,
            collection=os.getenv("RAG_CHROMA_COLLECTION", "openthai_legal"),
            local_path=os.getenv("RAG_CHROMA_PATH", str(ROOT / "data" / "chroma_local")),
            host=os.getenv("RAG_CHROMA_HOST") or None,
            port=int(os.getenv("RAG_CHROMA_PORT", "8000")),
        )
    elif VECTOR_BACKEND == "milvus":
        dense = MilvusDenseBackend(
            records,
            collection=os.getenv("RAG_MILVUS_COLLECTION", "openthai_legal"),
            uri=os.getenv("RAG_MILVUS_URI", str(ROOT / "data" / "milvus_legal.db")),
            recreate=False,
        )
    elif VECTOR_BACKEND == "memory":
        dense = MemoryDenseBackend(records)
    else:
        raise ValueError("RAG_VECTOR_BACKEND must be memory, qdrant, chroma, or milvus")
    engine = LegalHybridRetriever(records, embed_query=_embed_query, dense_backend=dense)
    _RETRIEVER_CACHE.clear()
    _RETRIEVER_CACHE[signature] = engine
    return engine


_THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")


def _section_number(value: object) -> str:
    """Return a stable Arabic section identifier, for example ``20/1``."""
    normalized = str(value or "").translate(_THAI_DIGITS)
    match = re.search(r"มาตรา\s*([0-9]+(?:\s*/\s*[0-9]+)?)", normalized)
    return re.sub(r"\s+", "", match.group(1)) if match else ""


def _referenced_sections(content: object) -> set[str]:
    normalized = str(content or "").translate(_THAI_DIGITS)
    return {
        re.sub(r"\s+", "", value)
        for value in re.findall(r"มาตรา\s*([0-9]+(?:\s*/\s*[0-9]+)?)", normalized)
    }


def _expanded_legal_query(query: str) -> str:
    """Translate common operational wording into statute vocabulary.

    The original question remains what the answer model sees. This lightweight
    expansion is only for first-stage retrieval, where users often say
    "screenshot to Line group" while the statute says "disclose or publish".
    """
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
    return f"{query}\n\nคำค้นตามถ้อยคำกฎหมาย: {' ; '.join(additions)}" if additions else query


def _legacy_hybrid_candidates(query: str, candidate_k: int) -> list[dict[str, Any]]:
    """Fuse BM25-style lexical and dense embedding rankings with RRF.

    A wider candidate set is deliberate: an LLM reranker can reject semantic
    near-misses only if the operative section has first survived retrieval.
    """
    corpus = _read_corpus()
    if not corpus or not query.strip():
        return []
    search_query = _expanded_legal_query(query)
    q_terms = _tokens(search_query)
    if not q_terms:
        return []

    doc_terms = [_tokens(f"{row.get('law_name', '')} {row.get('section', '')} {row.get('content', '')}") for row in corpus]
    document_frequency = Counter(term for terms in doc_terms for term in set(terms))
    average_length = max(1.0, sum(map(len, doc_terms)) / len(doc_terms))
    total = len(doc_terms)
    lexical_scores: list[float] = []
    for row, terms in zip(corpus, doc_terms):
        counts = Counter(terms)
        score = 0.0
        for term in set(q_terms):
            frequency = counts.get(term, 0)
            if not frequency:
                continue
            idf = math.log(1 + (total - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
            score += idf * (frequency * 2.0) / (frequency + 1.2 * (1 - 0.75 + 0.75 * len(terms) / average_length))
        lexical_scores.append(score)
    query_vector: list[float] = []
    try:
        query_vector = _embed_query(search_query)
    except Exception as exc:
        print(f"[rag-8083] embedding unavailable; lexical fallback: {exc}")
    maximum_lexical = max(lexical_scores) if lexical_scores else 0.0
    vector_scores: list[float] = []
    for row, lexical in zip(corpus, lexical_scores):
        vector_scores.append(_cosine(query_vector, list(row.get("embedding") or [])) if query_vector else 0.0)
    lexical_order = sorted(range(len(corpus)), key=lambda index: lexical_scores[index], reverse=True)
    vector_order = sorted(range(len(corpus)), key=lambda index: vector_scores[index], reverse=True)
    lexical_rank = {index: rank for rank, index in enumerate(lexical_order, start=1) if lexical_scores[index] > 0}
    vector_rank = {index: rank for rank, index in enumerate(vector_order, start=1) if vector_scores[index] > 0}
    # Reciprocal rank fusion avoids relying on incomparable BM25/cosine scales.
    rrf_k = 60
    scored: list[tuple[float, int, float, float, dict[str, Any]]] = []
    for index, row in enumerate(corpus):
        rank_l = lexical_rank.get(index)
        rank_v = vector_rank.get(index)
        if rank_l is None and rank_v is None:
            continue
        fused = (1 / (rrf_k + rank_l) if rank_l else 0.0) + (1 / (rrf_k + rank_v) if rank_v else 0.0)
        normalized_lexical = lexical_scores[index] / maximum_lexical if maximum_lexical else 0.0
        scored.append((fused, index, normalized_lexical, vector_scores[index], row))
    scored.sort(key=lambda item: item[0], reverse=True)
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for fused, _, lexical, vector, row in scored:
        law_name = str(row.get("instrument") or row.get("law_name") or "เอกสาร")
        section = str(row.get("clause") or row.get("section") or row.get("id") or "เนื้อหา")
        key = (law_name, section)
        if key in seen:
            continue
        seen.add(key)
        candidates.append({**row, "hybrid_score": fused, "lexical_score": lexical, "vector_score": vector})
        if len(candidates) >= candidate_k:
            break
    # Obligations and their penalties are frequently separate sections. For a
    # question that asks about legality or sanctions, add directly linked
    # penalty sections even when their wording has little lexical overlap with
    # the scenario (such as a screen-shot leak vs. "violates section 24").
    # Do not add them to ordinary information questions: that would dilute the
    # RAG context with irrelevant sanctions.
    sanction_intent = any(term in query for term in ("โทษ", "บทลงโทษ", "ระวาง", "ความผิด", "ผิดกฎหมาย", "ผลตามกฎหมาย", "จำคุก", "ปรับ"))
    primary_limit = max(12, candidate_k - 12)
    primary = candidates[:primary_limit]
    primary_sections = {_section_number(row.get("section") or row.get("clause")) for row in primary}
    primary_sections.discard("")
    linked: list[dict[str, Any]] = []
    existing_ids = {str(row.get("id")) for row in primary}
    if sanction_intent and primary_sections:
        for fused, _, lexical, vector, row in scored:
            if str(row.get("id")) in existing_ids:
                continue
            content = str(row.get("content", ""))
            if "ต้องระวางโทษ" not in content or not (_referenced_sections(content) & primary_sections):
                continue
            linked.append({
                **row,
                "hybrid_score": fused,
                "lexical_score": lexical,
                "vector_score": vector,
                "linked_penalty": True,
                "linked_to": sorted(_referenced_sections(content) & primary_sections),
            })
            existing_ids.add(str(row.get("id")))
            if len(linked) >= 12:
                break
    # Keep a sanction beside the obligation it enforces. This makes the
    # relationship visible to the reranker without relying on its ability to
    # connect two distant chunks in a long candidate list.
    merged: list[dict[str, Any]] = []
    linked_by_section: dict[str, list[dict[str, Any]]] = {}
    for row in linked:
        for section in row.get("linked_to", []):
            linked_by_section.setdefault(section, []).append(row)
    for row in primary:
        merged.append(row)
        section = _section_number(row.get("section") or row.get("clause"))
        for penalty in linked_by_section.get(section, []):
            if str(penalty.get("id")) not in {str(item.get("id")) for item in merged}:
                merged.append(penalty)
    for penalty in linked:
        if len(merged) >= candidate_k:
            break
        if str(penalty.get("id")) not in {str(item.get("id")) for item in merged}:
            merged.append(penalty)
    for row in candidates[primary_limit:]:
        if len(merged) >= candidate_k:
            break
        if str(row.get("id")) not in existing_ids:
            merged.append(row)
            existing_ids.add(str(row.get("id")))
    return merged[:candidate_k]


def _hybrid_candidates(query: str, candidate_k: int) -> list[dict[str, Any]]:
    """Generate a broad backend-neutral pool for OpenThai reranking."""
    hits = _retriever().search(
        query,
        profile=RETRIEVAL_PROFILE,
        top_k=candidate_k,
        candidate_k=candidate_k,
    )
    candidates = []
    for hit in hits:
        content = str(hit.record.get("content") or "")
        candidates.append(
            {
                **hit.record,
                "hybrid_score": hit.score,
                "lexical_score": hit.lexical_score or hit.fts_score,
                "vector_score": hit.dense_score,
                "fts_score": hit.fts_score,
                "retrieval_source": hit.source,
                "linked_penalty": hit.source == "linked_penalty",
                "linked_to": sorted(legal_referenced_sections(content)) if hit.source == "linked_penalty" else [],
            }
        )
    return candidates


def _parse_rerank_ids(content: str) -> list[str]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.I)
    options = [cleaned, *re.findall(r"\{.*\}", cleaned, flags=re.S)]
    for option in options:
        try:
            value = json.loads(option)
        except json.JSONDecodeError:
            continue
        ids = value.get("selected_ids", []) if isinstance(value, dict) else []
        if isinstance(ids, list):
            return [str(item) for item in ids if str(item).strip()]
    return []


def _rerank_with_openthai(query: str, candidates: list[dict[str, Any]], top_k: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Use OpenThai as a bounded legal evidence selector, with safe fallback."""
    if not candidates:
        return [], {"status": "no_candidates", "candidate_count": 0, "rerank_ms": 0.0}
    final_k = min(max(1, top_k), len(candidates))
    rows = []
    for row in candidates:
        section = row.get("clause") or row.get("section") or "เนื้อหา"
        content = str(row.get("content", ""))[:RERANK_CONTEXT_CHARS]
        rows.append(f"ID: {row['id']}\nแหล่ง: {row.get('instrument') or row.get('law_name') or 'เอกสาร'} {section}\nข้อความ: {content}")
    valid_ids = [str(row["id"]) for row in candidates]
    selection_schema = {
        "name": "legal_evidence_selection",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "selected_ids": {
                    "type": "array",
                    "items": {"type": "string", "enum": valid_ids},
                    "minItems": 1,
                    "maxItems": final_k,
                }
            },
            "required": ["selected_ids"],
            "additionalProperties": False,
        },
    }
    system = """คุณเป็นตัวคัดเลือกหลักฐานจากกฎหมายไทยสำหรับ RAG เท่านั้น
ให้อ่านคำถามและเลือกเฉพาะ ID ของมาตราที่ใช้ตอบข้อเท็จจริงโดยตรง ไม่ตอบคำถามกฎหมายเอง และห้ามสร้าง ID ใหม่
ให้ความสำคัญกับมาตราที่กำหนดหน้าที่ ข้อห้าม เงื่อนไข สิทธิ ระยะเวลา หรือบทลงโทษที่ตรงกับผู้กระทำและการกระทำในคำถาม
ถ้าคำถามมีหลายประเด็น ให้แยกผู้กระทำ การกระทำ หน้าที่ สิทธิ และผลทางกฎหมายแต่ละประเด็นก่อน แล้วเลือกมาตราที่ตรงอย่างน้อยหนึ่งมาตราต่อประเด็น โดยไม่ถือว่าจำนวนสูงสุดคือเป้าหมายที่ต้องเลือกให้ครบ
เมื่อคำถามระบุพนักงาน เจ้าหน้าที่ หรือผู้ปฏิบัติงาน ให้เลือกมาตราที่ระบุบุคคลผู้รู้ข้อมูลจากการทำงานหรือการปฏิบัติหน้าที่โดยตรงก่อนมาตราที่ใช้กับบริษัทหรือผู้ใช้บริการ เว้นแต่ข้อความของมาตราใช้กับพนักงานนั้นโดยชัดแจ้ง
ถ้าคำถามถามว่าผิดกฎหมายหรือมีโทษอย่างไร ให้เลือกทั้งมาตราหลักและมาตราโทษที่อ้างถึงมาตราหลักนั้นเท่าที่จำเป็น
ห้ามเลือกมาตราที่เพียงมีคำคล้ายกันแต่ใช้กับบุคคลหรือกรณีอื่น
ตอบเป็น JSON ตาม schema ที่กำหนดเท่านั้น"""
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"คำถาม:\n{query}\n\nหลักฐาน (เลือกได้ไม่เกิน {final_k} ID):\n\n" + "\n\n---\n\n".join(rows)},
        ],
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": 300,
        "seed": 42,
        "response_format": {"type": "json_schema", "json_schema": selection_schema},
        "chat_template_kwargs": {"enable_thinking": False},
    }
    started = time.perf_counter()
    try:
        raw = _request_json(VLLM_URL, payload, timeout=240)
        content = str(((raw.get("choices") or [{}])[0].get("message") or {}).get("content") or "")
        approved = _parse_rerank_ids(content)
        by_id = {str(row["id"]): row for row in candidates}
        # Preserve the reranker's ordering (most relevant first), while
        # rejecting duplicates or IDs that were not candidates.
        selected = []
        seen_ids: set[str] = set()
        sanction_intent = any(term in query for term in (
            "โทษ", "บทลงโทษ", "ระวาง", "ความผิด", "ผิดกฎหมาย",
            "ผลตามกฎหมาย", "ผลทางกฎหมาย", "ความรับผิด", "จำคุก", "ปรับ",
        ))
        linked_penalty_added = 0
        for selected_id in approved:
            if selected_id in by_id and selected_id not in seen_ids:
                selected_row = by_id[selected_id]
                selected.append(selected_row)
                seen_ids.add(selected_id)
                # The LLM ranks the evidence. For a sanction question, retain
                # the directly cross-referenced penalty next to any selected
                # operative section. This is a structural legal relation, not
                # a guessed citation, and prevents a relevant penalty from
                # being displaced by a generic near-match.
                if sanction_intent:
                    section = _section_number(selected_row.get("section") or selected_row.get("clause"))
                    for companion in candidates:
                        companion_content = str(companion.get("content", ""))
                        linked_to = set(companion.get("linked_to", [])) | _referenced_sections(companion_content)
                        if "ต้องระวางโทษ" not in companion_content or section not in linked_to:
                            continue
                        companion_id = str(companion["id"])
                        if companion_id not in seen_ids and len(selected) < final_k:
                            selected.append(companion)
                            seen_ids.add(companion_id)
                            linked_penalty_added += 1
            if len(selected) >= final_k:
                break
        # Do not pad with near-misses: the reranker's job is to minimize the
        # evidence set.
        if not selected:
            raise ValueError("reranker returned no valid candidate IDs")
        reranker_status = "openthai_json" if "openthai" in MODEL_NAME.lower() else "model_json"
        return selected, {"status": reranker_status, "candidate_count": len(candidates), "rerank_ms": round((time.perf_counter() - started) * 1000, 1), "rerank_usage": raw.get("usage", {}), "linked_penalty_added": linked_penalty_added}
    except Exception as exc:
        return candidates[:final_k], {"status": "hybrid_fallback", "candidate_count": len(candidates), "rerank_ms": round((time.perf_counter() - started) * 1000, 1), "detail": str(exc)[:240]}


def retrieve(query: str, top_k: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidates = _hybrid_candidates(query, HYBRID_CANDIDATE_K)
    selected, diagnostics = _rerank_with_openthai(query, candidates, top_k)
    diagnostics["retrieval_profile"] = RETRIEVAL_PROFILE
    diagnostics["vector_backend"] = VECTOR_BACKEND
    # Kept in the API diagnostics for reproducible retrieval evaluation; the
    # browser still renders only the final evidence selected by OpenThai.
    diagnostics["candidate_sections"] = [
        str(row.get("clause") or row.get("section") or "")
        for row in candidates
    ]
    results = []
    for rank, row in enumerate(selected, start=1):
        page = row.get("page_start") or row.get("page") or "?"
        clause = row.get("clause") or row.get("section") or "เนื้อหา"
        results.append({
            "citation": rank,
            "id": row["id"],
            "law_name": row.get("instrument") or row.get("law_name") or "เอกสาร",
            "section": f"{clause} · p.{page}",
            "content": row["content"],
            "source_url": row.get("source_url", ""),
            "score": round(float(row.get("hybrid_score", 0.0)), 4),
            "lexical_score": round(float(row.get("lexical_score", 0.0)), 4),
            "vector_score": round(float(row.get("vector_score", 0.0)), 4),
            "page_start": page,
            "clause": row.get("clause", ""),
            "retrieval_rank": rank,
            "rerank_status": diagnostics["status"],
        })
    diagnostics["selected_count"] = len(results)
    return results, diagnostics


def _answer_evidence(question: str, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compress reranked evidence to the smallest actor-aware answer context.

    The LLM reranker is deliberately given a broad candidate pool.  It can
    still return several legally adjacent sections; passing every one to the
    answer model encourages it to blend different actor scopes.  This helper
    only reorders/removes OpenThai-selected evidence and keeps an explicitly
    linked penalty beside the selected substantive section.
    """
    if len(hits) <= ANSWER_EVIDENCE_K:
        return hits
    expanded_terms = Counter(_tokens(_expanded_legal_query(question)))
    has_employee_actor = any(term in question.lower() for term in ("พนักงาน", "เจ้าหน้าที่", "ผู้ปฏิบัติงาน", "ปฏิบัติหน้าที่"))
    scored: list[tuple[float, int, dict[str, Any]]] = []
    for index, hit in enumerate(hits):
        content = str(hit.get("content", ""))
        terms = Counter(_tokens(content))
        score = float(sum(min(count, terms.get(term, 0)) for term, count in expanded_terms.items()))
        if has_employee_actor:
            if "ผู้ซึ่งรู้ข้อมูลจากการทำงาน" in content or "จากการปฏิบัติหน้าที่" in content:
                score += 1_000.0
            if "ผู้ใช้บริการ" in content and "ผู้ซึ่งรู้ข้อมูลจากการทำงาน" not in content:
                score -= 50.0
        # Prefer an operative section as the anchor; penalties are attached
        # below through an explicit statutory cross-reference.
        if "ต้องระวางโทษ" in content:
            score -= 200.0
        scored.append((score, index, hit))
    scored.sort(key=lambda item: (-item[0], item[1]))
    anchor = scored[0][2]
    compact = [anchor]
    anchor_section = _section_number(anchor.get("section"))
    for _, _, hit in scored:
        if len(compact) >= ANSWER_EVIDENCE_K:
            break
        content = str(hit.get("content", ""))
        if hit is anchor or "ต้องระวางโทษ" not in content:
            continue
        if anchor_section and anchor_section in _referenced_sections(content):
            compact.append(hit)
    for _, _, hit in scored:
        if len(compact) >= ANSWER_EVIDENCE_K:
            break
        if hit not in compact:
            compact.append(hit)
    # Renumber citations after compaction so the model and the browser see
    # one unambiguous citation map.
    return [{**hit, "citation": rank} for rank, hit in enumerate(compact, start=1)]


def _citation_evidence_plan(question: str, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Produce a focused open-book packet from the LLM-reranked candidates.

    OpenThai is strong when supplied with the exact provisions and ordinary
    distractors, but live NCB tests exposed actor-confusable hard negatives.
    These rules use statutory wording and cross-references, never hard-coded
    section numbers, to form a small packet before citation generation.
    """
    if not hits:
        return []
    lower = question.lower()
    broker_intent = any(term in lower for term in ("ตัวกลาง", "จัดหาสินเชื่อ", "loan broker", "แพลตฟอร์มสินเชื่อ"))
    pool = [
        hit for hit in hits
        if broker_intent or "สมาชิกประเภทผู้ประกอบธุรกิจเป็นตัวกลางในการจัดหาสินเชื่อ" not in str(hit.get("content", ""))
    ]
    if not pool:
        pool = hits

    def finish(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        unique: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            identifier = str(row.get("id"))
            if identifier not in seen:
                unique.append(row)
                seen.add(identifier)
        return [{**row, "citation": rank} for rank, row in enumerate(unique[:6], start=1)]

    # Employee confidentiality: choose the operative provision that expressly
    # covers a person learning data from work, plus a penalty that references
    # it. This excludes offences limited to employees of a different entity.
    if any(term in lower for term in ("พนักงาน", "เจ้าหน้าที่", "ผู้ปฏิบัติงาน")):
        anchors = [
            hit for hit in pool
            if "ผู้ซึ่งรู้ข้อมูลจากการทำงาน" in str(hit.get("content", ""))
            or "ผู้ซึ่งรู้ข้อมูลจากการปฏิบัติหน้าที่" in str(hit.get("content", ""))
        ]
        if anchors:
            anchor = anchors[0]
            anchor_section = _section_number(anchor.get("section"))
            companions = [
                hit for hit in pool
                if "ต้องระวางโทษ" in str(hit.get("content", ""))
                and anchor_section in _referenced_sections(hit.get("content", ""))
            ]
            return finish([anchor, *companions])

    # Licensing questions usually need both the positive licence condition and
    # a short exclusivity prohibition. Short provisions must not be discarded
    # merely because they carry fewer lexical terms.
    if any(term in lower for term in ("ใบอนุญาต", "ตั้งบริษัท", "ประกอบธุรกิจข้อมูลเครดิต")):
        licensing = [
            hit for hit in pool
            if "ได้รับใบอนุญาตจากรัฐมนตรี" in str(hit.get("content", ""))
            or "ห้ามมิให้ผู้ใดนอกจากบริษัทข้อมูลเครดิต" in str(hit.get("content", ""))
        ]
        if licensing:
            return finish(licensing)

    # Multi-control lifecycle questions map each explicit operational risk to
    # the one provision that contains the corresponding statutory language.
    if any(term in lower for term in ("เกินอายุ", "นอกประเทศไทย", "ภายนอกราชอาณาจักร", "ข้อมูลห้ามจัดเก็บ")):
        cues = ("จัดเก็บข้อมูลห้ามจัดเก็บ", "ภายนอกราชอาณาจักร", "อายุของข้อมูลเกิน")
        lifecycle: list[dict[str, Any]] = []
        for cue in cues:
            lifecycle.extend(hit for hit in pool if cue in str(hit.get("content", "")))
        if lifecycle:
            return finish(lifecycle)

    # Purpose limitation / cross-selling: keep the disclosure purpose and the
    # recipient's duty, after excluding provisions limited to loan brokers.
    if any(term in lower for term in ("cross-selling", "การตลาด", "บริษัทประกัน", "เสนอขาย")):
        purpose = [
            hit for hit in pool
            if "ประโยชน์ในการวิเคราะห์สินเชื่อและการออกบัตรเครดิต" in str(hit.get("content", ""))
            or "ใช้ข้อมูลตามวัตถุประสงค์ที่กำหนด" in str(hit.get("content", ""))
        ]
        if purpose:
            return finish(purpose)

    # Consent questions should use the ordinary member disclosure provision;
    # loan-broker variants were already removed unless the question says so.
    if any(term in lower for term in ("ยินยอม", "consent", "ดึงข้อมูลเครดิต", "e-consent")):
        consent = [
            hit for hit in pool
            if "ได้รับความยินยอมจากเจ้าของข้อมูลก่อนทุกครั้ง" in str(hit.get("content", ""))
        ]
        if consent:
            return finish(consent)

    # If the principal provision incorporates follow-up sections, include
    # those candidates when the user asks about dispute, appeal, or next steps.
    if any(term in lower for term in ("โต้แย้ง", "อุทธรณ์", "ขั้นตอน", "สิทธิ", "พิจารณาอีกครั้ง")):
        anchors = [
            hit for hit in pool
            if "ปฏิเสธการให้สินเชื่อ" in str(hit.get("content", ""))
            or "แสดงเหตุผล" in str(hit.get("content", ""))
        ]
        if anchors:
            referenced = _referenced_sections(anchors[0].get("content", ""))
            companions = [
                hit for hit in pool
                if _section_number(hit.get("section")) in referenced
            ]
            return finish([anchors[0], *companions])

    return _answer_evidence(question, pool)


def _ensure_citation_footer(answer: str, hits: list[dict[str, Any]]) -> str:
    """Make source mapping visible when a generation omits its [n] markers."""
    if not hits or re.search(r"\[\d+\]", answer):
        return answer
    mapping = "; ".join(f"[{hit['citation']}] {hit['law_name']} {hit['section']}" for hit in hits)
    return answer.rstrip() + f"\n\nอ้างอิงหลักฐานที่ใช้: {mapping}"


def _structured_answer(content: str) -> tuple[str, list[dict[str, str]]]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.I)
    candidates = [cleaned, *re.findall(r"\{.*\}", cleaned, flags=re.S)]
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict) or not isinstance(payload.get("answer"), str):
            continue
        citations = payload.get("citations") if isinstance(payload.get("citations"), list) else []
        return payload["answer"], [
            {"law": str(item.get("law", "")), "section": str(item.get("section", ""))}
            for item in citations
            if isinstance(item, dict)
        ]
    return content, []


def _request_json(url: str, data: dict[str, Any] | None = None, timeout: int = 180) -> dict[str, Any]:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8") if data is not None else None
    request = urllib.request.Request(url, data=body, method="POST" if body else "GET")
    request.add_header("Accept", "application/json")
    if body:
        request.add_header("Content-Type", "application/json; charset=utf-8")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _evidence_prompt(hits: list[dict[str, Any]]) -> str:
    if not hits:
        return "ไม่มีหลักฐานในคลัง RAG ที่ตรงกับคำถามนี้"
    # Evidence remains complete at the structural-section level; the budget is
    # large enough for six legal chunks but protects the answer context.
    citation_map = []
    entries = []
    remaining = EVIDENCE_CHAR_BUDGET
    for hit in hits:
        if remaining <= 0:
            break
        content = hit["content"][: min(6_000, remaining)]
        remaining -= len(content)
        source_url = f"\nSource URL: {hit['source_url']}" if hit.get("source_url") else ""
        citation_map.append(f"[{hit['citation']}] = {hit['law_name']} {hit['section']}")
        entries.append(f"[{hit['citation']}] {hit['law_name']} {hit['section']}{source_url}\n{content}")
    return "ตารางอ้างอิงที่ต้องใช้ตรงตัว:\n" + "\n".join(citation_map) + "\n\nข้อความหลักฐานเต็ม:\n\n" + "\n\n".join(entries)


GENERATION_PROFILES = {
    "citation_rag": {"temperature": 0.0, "top_p": 1.0, "max_tokens": 2048, "thinking": False, "rag_inject": "user"},
    "legal_essay": {"temperature": 0.7, "top_p": 0.9, "max_tokens": 4096, "thinking": False, "rag_inject": "system"},
    "legal_essay_thinking": {"temperature": 0.7, "top_p": 0.9, "max_tokens": 6144, "thinking": True, "rag_inject": "system"},
    "general_legal_chat": {"temperature": 0.7, "top_p": 0.9, "max_tokens": 2048, "thinking": False, "rag_inject": "user"},
    "closed_book": {"temperature": 0.0, "top_p": 1.0, "max_tokens": 2048, "thinking": False, "rag_inject": "none"},
}


def _xml_evidence(hits: list[dict[str, Any]]) -> str:
    blocks = []
    for hit in hits:
        section = _section_number(hit.get("section") or hit.get("clause"))
        blocks.append(
            f'<law law_name="{hit["law_name"]}" section="{section}">\n'
            f'{hit["content"]}\n</law>'
        )
    return "\n\n".join(blocks) if blocks else "(no retrieved statutory context)"


def ask_vllm(
    question: str,
    history: list[dict[str, str]],
    hits: list[dict[str, Any]],
    *,
    mode: str,
) -> tuple[dict[str, Any], float, dict[str, Any]]:
    if mode not in GENERATION_PROFILES:
        raise ValueError(f"unknown generation mode: {mode}")
    profile = dict(GENERATION_PROFILES[mode])
    evidence = _evidence_prompt(hits)
    user_content = question
    response_format: dict[str, Any] | None = None
    if mode == "citation_rag":
        # Exact quickstart contract from the released model card. Live tests
        # showed that constrained JSON decoding changes section selection, so
        # JSON validity is checked after generation instead.
        assistant_identity = (
            "You are OpenThaiGPT-Legal, an expert assistant on Thai law"
            if "openthai" in MODEL_NAME.lower()
            else "You are an expert assistant on Thai law"
        )
        system = (
            f"{assistant_identity}. You are given a legal "
            "question and the exact statutory sections needed to answer it. Reason step by step in "
            "English, then give the final answer in Thai. Cite ONLY sections present in the provided "
            "context, using each section's exact law_name and bare section number (e.g. 132, 77/1). "
            'Output the final answer as JSON: {"answer": "<Thai answer>", '
            '"citations": [{"law": "<law_name>", "section": "<bare id>"}]}.'
        )
        user_content = f"Provided context:\n{_xml_evidence(hits)}\n\nQuestion (ตอบเป็นภาษาไทย):\n{question}"
    elif mode == "closed_book":
        system = (
            "You are an expert on Thai law. You are given ONLY a legal question, with NO reference "
            "material provided. Using your OWN knowledge of Thai statutes, answer in Thai and cite the "
            "specific sections that apply (law name + bare section number, มาตรา). "
            'Output ONLY a JSON object: {"answer":"<Thai answer>","citations":[{"law":"<law name>",'
            '"section":"<bare section number e.g. 40 or 77/1>"}]}.'
        )
    elif mode in {"legal_essay", "legal_essay_thinking"}:
        system = """You are a Thai legal expert. Answer the question with legal analysis and cite the relevant มาตรา.
เมื่อมีหลักฐานประกอบ ให้อ้างเฉพาะมาตราจากหลักฐาน หากหลักฐานไม่พอให้ระบุช่องว่าง
ถ้าไม่มีหลักฐานประกอบ ให้อ้างได้เฉพาะเลขมาตราที่โจทย์ระบุไว้ชัดแจ้ง ห้ามเติมเลขมาตราอื่นจากการคาดเดา

หลักฐานประกอบ:
""" + evidence
    else:
        system = """คุณคือผู้ช่วยสนทนาด้านกฎหมายไทย ตอบเป็นภาษาไทยทุกครั้ง ให้ข้อมูลที่เข้าใจง่าย ถามกลับเมื่อข้อเท็จจริงสำคัญไม่ครบ
แยกข้อมูลทั่วไปออกจากข้อสรุปทางกฎหมาย และเตือนให้ตรวจฉบับกฎหมายปัจจุบันเมื่อเป็นเรื่องสำคัญ

หลักฐานที่ค้นได้:
""" + evidence

    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for item in history[-6:]:
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_content})
    payload: dict[str, Any] = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": profile["temperature"],
        "top_p": profile["top_p"],
        "max_tokens": profile["max_tokens"],
        "chat_template_kwargs": {"enable_thinking": profile["thinking"]},
    }
    if response_format:
        payload["response_format"] = response_format
    started = time.perf_counter()
    answer = _request_json(VLLM_URL, payload)
    return answer, (time.perf_counter() - started) * 1000, profile


def _legacy_answer_system(evidence: str) -> str:
    """Retained as a readable reference for the earlier free-form RAG prompt."""
    return """คุณคือ OpenThai Legal RAG Assistant สำหรับการวิเคราะห์กฎหมาย ระเบียบ และหลักฐานของธนาคารไทย
ตอบเป็นภาษาไทยอย่างรอบคอบ กระชับ และแยก “ข้อกำหนด/ข้อเท็จจริงจากเอกสาร” ออกจาก “แนวทางตรวจสอบของ IT Audit”

กฎหลักฐาน RAG ที่ต้องปฏิบัติเคร่งครัด:
1. หลักฐานด้านล่างเป็นแหล่งเดียวที่อนุญาตให้ใช้ตอบเชิงกฎหมายหรือข้อเท็จจริง และบาง chunk อาจเป็น distractor โดยตั้งใจ
2. ทุกข้อความอ้างอิงข้อเท็จจริง กฎ ตัวเลข วันที่ หรือข้อสรุปจากหลักฐาน ต้องมี citation รูปแบบ [เลข] ในประโยคเดียวกัน
3. ก่อนอ้าง “มาตรา X” ต้องตรวจตารางอ้างอิง: citation [เลข] ที่วางท้ายประโยคต้องเป็นมาตรา X เดียวกันอย่างแท้จริง ห้ามใช้ [เลข] ของคนละมาตรา
4. เมื่อหลักฐานใช้กับบุคคลต่างบทบาทกัน (เช่น ผู้ใช้บริการ บริษัท หรือพนักงานผู้รู้ข้อมูลจากงาน) ให้แยกเงื่อนไขการใช้ให้ชัดเจน ห้ามรวมเป็นฐานเดียวกันโดยไม่มีข้อความรองรับ
5. ห้ามสร้างมาตรา ข้อ กำหนดเวลา หรือชื่อหน่วยงานที่ไม่มีในหลักฐาน
6. ถ้าหลักฐานไม่มีข้อความที่ตอบคำถามโดยตรง ให้ระบุ “evidence gap” อย่างชัดเจน ห้ามเดาและห้ามใช้ chunk ที่คล้ายคำแต่คนละหัวข้อ
7. อย่าคัดลอกข้อความหลักฐานยาว ๆ; สรุปเฉพาะที่ตอบคำถามและอ้าง [เลข]

คำตอบเป็นข้อมูลทั่วไป ไม่ใช่คำปรึกษากฎหมายเฉพาะกรณี

หลักฐาน RAG (คงข้อความตามต้นฉบับ):
""" + evidence


DEMO_ROWS = [
    {
        "id": "demo-420",
        "law_name": "ประมวลกฎหมายแพ่งและพาณิชย์ (ตัวอย่างเพื่อทดสอบ)",
        "section": "มาตรา 420",
        "content": "ผู้ใดจงใจหรือประมาทเลินเล่อ ทำต่อบุคคลอื่นโดยผิดกฎหมายให้เขาเสียหายถึงแก่ชีวิตก็ดี แก่ร่างกายก็ดี อนามัยก็ดี เสรีภาพก็ดี ทรัพย์สินหรือสิทธิอย่างหนึ่งอย่างใดก็ดี ท่านว่าผู้นั้นทำละเมิด จำต้องใช้ค่าสินไหมทดแทนเพื่อการนั้น",
    },
    {
        "id": "demo-328",
        "law_name": "ประมวลกฎหมายแพ่งและพาณิชย์ (ตัวอย่างเพื่อทดสอบ)",
        "section": "มาตรา 328",
        "content": "ถ้าการใดอันได้กระทำไปให้เสียหายแก่ชื่อเสียงของบุคคลอื่น เป็นการฝ่าฝืนต่อความจริงไซร้ ท่านว่าผู้เสียหายจะเรียกให้จัดการตามวิธีอื่นเพื่อบรรเทาความเสียหายก็ได้",
    },
    {
        "id": "demo-335",
        "law_name": "ประมวลกฎหมายอาญา (ตัวอย่างเพื่อทดสอบ)",
        "section": "มาตรา 335",
        "content": "ผู้ใดลักทรัพย์ในเวลากลางคืน หรือในสถานที่และพฤติการณ์ตามที่กฎหมายกำหนด ต้องระวางโทษหนักขึ้นตามบทบัญญัตินี้",
    },
]


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[rag-8083] {self.address_string()} - {format % args}")

    def _json(self, payload: dict[str, Any], status: int = HTTPStatus.OK) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 2_000_000:
            raise ValueError("Payload is too large")
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("JSON object required")
        return parsed

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            try:
                models = _request_json(VLLM_MODELS_URL, timeout=5)
                with _db_connection() as connection, connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                self._json({
                    "ok": True,
                    "vllm": "ready",
                    "postgres": "ready",
                    "model": MODEL_NAME,
                    "models": [item.get("id") for item in models.get("data", [])],
                    "corpus_count": len(_read_corpus()),
                    "retrieval_profile": RETRIEVAL_PROFILE,
                    "vector_backend": VECTOR_BACKEND,
                    "candidate_k": HYBRID_CANDIDATE_K,
                    "rerank_context_chars": RERANK_CONTEXT_CHARS,
                    "answer_evidence_k": ANSWER_EVIDENCE_K,
                })
            except Exception as exc:
                self._json({"ok": False, "detail": str(exc), "corpus_count": len(_read_corpus())}, HTTPStatus.SERVICE_UNAVAILABLE)
            return
        if parsed.path == "/api/corpus":
            items = _read_corpus()
            self._json({"items": items, "count": len(items)})
            return
        if parsed.path == "/api/sessions":
            requested = parse_qs(parsed.query).get("limit", ["20"])[0]
            self._json({"items": list_sessions(int(requested))})
            return
        if parsed.path.startswith("/api/sessions/"):
            session = get_session(parsed.path.rsplit("/", 1)[-1])
            if not session:
                self._json({"error": "ไม่พบ session"}, HTTPStatus.NOT_FOUND)
                return
            self._json(session)
            return
        if self.path in {"/", "/index.html"}:
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        try:
            data = self._body()
            if self.path == "/api/sessions":
                self._json({"session": create_session(str(data.get("title", "")))}, HTTPStatus.CREATED)
                return
            if self.path == "/api/retrieve":
                query = str(data.get("query", "")).strip()
                top_k = max(1, min(int(data.get("top_k", 10)), 20))
                started = time.perf_counter()
                hits, diagnostics = retrieve(query, top_k)
                self._json({"hits": hits, "retrieval_ms": round((time.perf_counter() - started) * 1000, 1), "retrieval": diagnostics})
                return
            if self.path == "/api/corpus":
                law_name = str(data.get("law_name", "")).strip()
                section = str(data.get("section", "")).strip()
                content = str(data.get("content", "")).strip()
                source_url = str(data.get("source_url", "")).strip()
                if not law_name or not section or len(content) < 20:
                    self._json({"error": "กรอกชื่อกฎหมาย มาตรา และเนื้อหาอย่างน้อย 20 ตัวอักษร"}, HTTPStatus.BAD_REQUEST)
                    return
                items = _read_corpus()
                row = {"id": str(uuid.uuid4()), "law_name": law_name[:240], "section": section[:120], "content": content[:24000], "source_url": source_url[:2048]}
                items.append(row)
                _write_corpus(items)
                self._json({"ok": True, "item": row, "count": len(items)}, HTTPStatus.CREATED)
                return
            if self.path == "/api/corpus/demo":
                items = _read_corpus()
                existing = {item.get("id") for item in items}
                items.extend(row for row in DEMO_ROWS if row["id"] not in existing)
                _write_corpus(items)
                self._json({"ok": True, "count": len(items), "added": len([row for row in DEMO_ROWS if row["id"] not in existing])})
                return
            if self.path == "/api/chat":
                question = str(data.get("question", "")).strip()
                if not question:
                    self._json({"error": "กรุณาระบุคำถาม"}, HTTPStatus.BAD_REQUEST)
                    return
                mode = str(data.get("mode", "citation_rag")).strip()
                if mode not in GENERATION_PROFILES:
                    raise ValueError(f"โหมดไม่ถูกต้อง: {mode}")
                top_k = max(1, min(int(data.get("top_k", 10)), 20))
                use_rag = bool(data.get("use_rag", True)) and mode != "closed_book"
                session = _resolve_session(data.get("session_id"), question[:160])
                session_id = session["id"]
                history = _history_for_model(session_id)
                _save_message(session_id, "user", question)
                all_started = time.perf_counter()
                retrieve_started = time.perf_counter()
                retrieval_query = question
                if mode == "general_legal_chat" and any(
                    term in question for term in ("ก่อนหน้า", "ดังกล่าว", "นั้น", "สองคำตอบ", "สรุป")
                ):
                    previous_user = next(
                        (item["content"] for item in reversed(history) if item.get("role") == "user"),
                        "",
                    )
                    if previous_user:
                        retrieval_query = f"{previous_user}\nคำถามต่อเนื่อง: {question}"
                hits, retrieval = retrieve(retrieval_query, top_k) if use_rag else ([], {
                    "status": "disabled",
                    "candidate_count": 0,
                    "selected_count": 0,
                    "rerank_ms": 0.0,
                    "retrieval_profile": "none",
                    "vector_backend": "none",
                })
                retrieval_ms = (time.perf_counter() - retrieve_started) * 1000
                if mode in {"legal_essay", "legal_essay_thinking"}:
                    answer_hits = _citation_evidence_plan(question, hits) if use_rag else []
                elif mode == "citation_rag":
                    answer_hits = _citation_evidence_plan(question, hits)
                else:
                    answer_hits = _citation_evidence_plan(retrieval_query, hits) if use_rag else []
                raw, generation_ms, generation_profile = ask_vllm(
                    question,
                    history,
                    answer_hits,
                    mode=mode,
                )
                choice = (raw.get("choices") or [{}])[0]
                message = choice.get("message") or {}
                raw_content = message.get("content") or ""
                answer, model_citations = _structured_answer(raw_content) if mode == "citation_rag" else (raw_content, [])
                if mode == "citation_rag":
                    answer = _ensure_citation_footer(answer, answer_hits)
                reasoning = message.get("reasoning_content") or ""
                timing = {"retrieval_ms": round(retrieval_ms, 1), "generation_ms": round(generation_ms, 1), "total_ms": round((time.perf_counter() - all_started) * 1000, 1), "candidate_count": retrieval["candidate_count"], "selected_count": retrieval["selected_count"], "answer_evidence_count": len(answer_hits), "rerank_ms": retrieval["rerank_ms"], "rerank_status": retrieval["status"], "mode": mode}
                _save_message(session_id, "assistant", answer, reasoning=reasoning, citations=answer_hits, usage=raw.get("usage", {}), timing=timing)
                self._json({
                    "session": {key: session[key] for key in ("id", "title", "created_at", "updated_at")},
                    "answer": answer,
                    "reasoning": reasoning,
                    "citations": answer_hits,
                    "retrieval": retrieval,
                    "mode": mode,
                    "generation_profile": generation_profile,
                    "model_citations": model_citations,
                    "usage": raw.get("usage", {}),
                    "finish_reason": choice.get("finish_reason", ""),
                    "timing": timing,
                })
                return
            self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except (ValueError, json.JSONDecodeError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            self._json({"error": f"vLLM returned HTTP {exc.code}", "detail": detail}, HTTPStatus.BAD_GATEWAY)
        except (urllib.error.URLError, TimeoutError) as exc:
            self._json({"error": "ไม่สามารถเชื่อม vLLM ที่ 127.0.0.1:3033", "detail": str(exc)}, HTTPStatus.BAD_GATEWAY)
        except Exception as exc:  # keep client errors inspectable without crashing server
            self._json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8083), Handler)
    print(f"Legal RAG Lab ({MODEL_NAME}): http://0.0.0.0:8083")
    server.serve_forever()
