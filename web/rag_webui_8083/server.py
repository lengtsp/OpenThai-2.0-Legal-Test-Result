#!/usr/bin/env python3
"""OpenThai Legal RAG workbench, backed by a local vLLM OpenAI-compatible API.

The service deliberately keeps the corpus lightweight and inspectable: every
retrieved item has a source title and section, and the exact chunk that was
given to the model is returned to the browser as citation evidence.
"""

from __future__ import annotations

import json
import math
import os
import re
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


ROOT = Path(__file__).resolve().parent
CORPUS_PATH = ROOT / "data" / "legal_corpus.json"
VLLM_URL = "http://127.0.0.1:3033/v1/chat/completions"
VLLM_MODELS_URL = "http://127.0.0.1:3033/v1/models"
MODEL_NAME = "openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b"


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


def retrieve(query: str, top_k: int) -> list[dict[str, Any]]:
    corpus = _read_corpus()
    if not corpus or not query.strip():
        return []
    q_terms = _tokens(query)
    if not q_terms:
        return []

    doc_terms = [_tokens(f"{row.get('law_name', '')} {row.get('section', '')} {row.get('content', '')}") for row in corpus]
    document_frequency = Counter(term for terms in doc_terms for term in set(terms))
    average_length = max(1.0, sum(map(len, doc_terms)) / len(doc_terms))
    total = len(doc_terms)
    scored: list[tuple[float, dict[str, str]]] = []
    for row, terms in zip(corpus, doc_terms):
        counts = Counter(terms)
        score = 0.0
        for term in set(q_terms):
            frequency = counts.get(term, 0)
            if not frequency:
                continue
            idf = math.log(1 + (total - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
            score += idf * (frequency * 2.0) / (frequency + 1.2 * (1 - 0.75 + 0.75 * len(terms) / average_length))
        if score > 0:
            scored.append((score, row))
    scored.sort(key=lambda item: item[0], reverse=True)
    results = []
    for rank, (score, row) in enumerate(scored[:top_k], start=1):
        results.append({
            "citation": rank,
            "id": row["id"],
            "law_name": row["law_name"],
            "section": row["section"],
            "content": row["content"],
            "source_url": row.get("source_url", ""),
            "score": round(score, 3),
        })
    return results


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
    # Keep evidence under the 4k-token vLLM test context while retaining the
    # start of each source verbatim. The UI still returns the complete source.
    entries = []
    remaining = 10_000
    for hit in hits:
        if remaining <= 0:
            break
        content = hit["content"][: min(4_500, remaining)]
        remaining -= len(content)
        source_url = f"\nSource URL: {hit['source_url']}" if hit.get("source_url") else ""
        entries.append(f"[{hit['citation']}] {hit['law_name']} {hit['section']}{source_url}\n{content}")
    return "\n\n".join(entries)


def ask_vllm(question: str, history: list[dict[str, str]], hits: list[dict[str, Any]], *, thinking: bool, temperature: float, max_tokens: int) -> tuple[dict[str, Any], float]:
    evidence = _evidence_prompt(hits)
    system = """คุณคือ OpenThai Legal Assistant สำหรับการวิเคราะห์กฎหมายไทย
ตอบเป็นภาษาไทยอย่างรอบคอบ กระชับ และแยกข้อเท็จจริงออกจากข้อสรุป

กฎหลักฐาน RAG ที่ต้องปฏิบัติเคร่งครัด:
1. หลักฐานด้านล่างเป็นแหล่งเดียวที่อนุญาตให้ใช้ตอบเชิงกฎหมายหรือข้อเท็จจริง และบาง chunk อาจเป็น distractor โดยตั้งใจ
2. ทุกข้อความอ้างอิงข้อเท็จจริง กฎ ตัวเลข วันที่ หรือข้อสรุปจากหลักฐาน ต้องมี citation รูปแบบ [เลข] ในประโยคเดียวกัน
3. ห้ามอนุมานข้ามหัวข้อ: หลักฐานเรื่อง FX ไม่ได้พิสูจน์ข้อกำหนดใบอนุญาตสินทรัพย์ดิจิทัล และข้อความที่ไม่มีคำว่า “มาตรา” ไม่ใช่มาตรากฎหมาย
4. ถ้าหลักฐานไม่มีข้อความที่ตอบคำถามโดยตรง ให้ตอบเพียงว่า “หลักฐาน RAG ที่มีไม่ครอบคลุมคำถามนี้ จึงไม่สามารถยืนยันได้” แล้วระบุว่าต้องหาแหล่งทางการใดเพิ่ม ห้ามเดา ห้ามสร้างเลขมาตรา ห้ามใช้ chunk ที่คล้ายคำแต่คนละหัวข้อ
5. อย่าคัดลอกข้อความหลักฐานยาว ๆ; สรุปเฉพาะที่ตอบคำถามและอ้าง [เลข]

คำตอบเป็นข้อมูลทั่วไป ไม่ใช่คำปรึกษากฎหมายเฉพาะกรณี

หลักฐาน RAG (คงข้อความตามต้นฉบับ):
""" + evidence
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for item in history[-6:]:
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question})
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": max(0.0, min(float(temperature), 1.5)),
        "max_tokens": max(128, min(int(max_tokens), 4096)),
        "chat_template_kwargs": {"enable_thinking": bool(thinking)},
    }
    started = time.perf_counter()
    answer = _request_json(VLLM_URL, payload)
    return answer, (time.perf_counter() - started) * 1000


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
                self._json({"ok": True, "vllm": "ready", "postgres": "ready", "models": [item.get("id") for item in models.get("data", [])], "corpus_count": len(_read_corpus())})
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
                top_k = max(1, min(int(data.get("top_k", 4)), 8))
                started = time.perf_counter()
                hits = retrieve(query, top_k)
                self._json({"hits": hits, "retrieval_ms": round((time.perf_counter() - started) * 1000, 1)})
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
                top_k = max(1, min(int(data.get("top_k", 4)), 8))
                use_rag = bool(data.get("use_rag", True))
                session = _resolve_session(data.get("session_id"), question[:160])
                session_id = session["id"]
                history = _history_for_model(session_id)
                _save_message(session_id, "user", question)
                all_started = time.perf_counter()
                retrieve_started = time.perf_counter()
                hits = retrieve(question, top_k) if use_rag else []
                retrieval_ms = (time.perf_counter() - retrieve_started) * 1000
                raw, generation_ms = ask_vllm(question, history, hits, thinking=bool(data.get("thinking", False)), temperature=float(data.get("temperature", 0.2)), max_tokens=int(data.get("max_tokens", 1024)))
                choice = (raw.get("choices") or [{}])[0]
                message = choice.get("message") or {}
                answer = message.get("content") or ""
                reasoning = message.get("reasoning_content") or ""
                timing = {"retrieval_ms": round(retrieval_ms, 1), "generation_ms": round(generation_ms, 1), "total_ms": round((time.perf_counter() - all_started) * 1000, 1)}
                _save_message(session_id, "assistant", answer, reasoning=reasoning, citations=hits, usage=raw.get("usage", {}), timing=timing)
                self._json({
                    "session": {key: session[key] for key in ("id", "title", "created_at", "updated_at")},
                    "answer": answer,
                    "reasoning": reasoning,
                    "citations": hits,
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
    print("OpenThai Legal RAG workbench: http://0.0.0.0:8083")
    server.serve_forever()
