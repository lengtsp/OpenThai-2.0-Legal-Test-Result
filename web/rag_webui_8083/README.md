# OpenThai Legal RAG Workbench

เว็บ local สำหรับทดสอบ OpenThai 2.0 Legal ผ่าน vLLM พร้อม:

- Citation RAG, Closed-book, Legal essay, Legal essay thinking และ General legal chat
- Dense + BM25 + SQLite FTS5 hybrid candidate generation
- OpenThai reranker และ focused statutory evidence planner
- Qdrant, Chroma, Milvus หรือ in-memory dense backend
- PostgreSQL chat sessions
- สถานะโหลด เวลา retrieval/rerank/generation และหลักฐานใต้ message

## เตรียมระบบ

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
psql -h 127.0.0.1 -p 5432 -d opengpt -f schema.sql
```

เริ่ม OpenThai vLLM ที่ `127.0.0.1:3033` และ OpenAI-compatible embedding
service ที่ `127.0.0.1:8082` ก่อน

```bash
export OPENGPT_DB_USER='your_user'
export OPENGPT_DB_PASSWORD='your_password'
export RAG_CORPUS_PATH='/absolute/path/to/structural_legal_chunks.json'
export RAG_VECTOR_BACKEND='memory'
python server.py
```

เปิด <http://127.0.0.1:8083>

## Corpus schema

ไฟล์ corpus เป็น JSON array:

```json
[
  {
    "id": "stable-id",
    "law_name": "ชื่อกฎหมาย",
    "section": "24",
    "content": "ข้อความมาตรา",
    "page_start": 18,
    "page_end": 18,
    "source_url": "https://official.example/law.pdf"
  }
]
```

ใช้หนึ่งมาตราต่อหนึ่ง chunk และควรเพิ่ม `effective_date`, `content_hash`
และ metadata ของฉบับแก้ไขในงานจริง

## Vector backend

ค่าเริ่มต้น `memory` ไม่ต้องติดตั้ง vector database เพิ่ม หากใช้ backend อื่น:

```bash
export RAG_VECTOR_BACKEND=qdrant
export RAG_QDRANT_URL=http://127.0.0.1:6333

# หรือ
export RAG_VECTOR_BACKEND=chroma
export RAG_CHROMA_HOST=127.0.0.1
export RAG_CHROMA_PORT=8004

# หรือ
export RAG_VECTOR_BACKEND=milvus
export RAG_MILVUS_URI=http://127.0.0.1:19530
```

Docker Compose อยู่ที่ [`../../deploy/vector_stores`](../../deploy/vector_stores/)

## Production notes

ตัวอย่างนี้ bind เว็บที่ `0.0.0.0:8083` เพื่อให้ผู้ทดสอบในเครือข่ายเข้าถึง
ได้ แต่ไม่มี authentication/TLS/rate limit จึงไม่ควรเปิดสู่ Internet
โดยตรง และต้องแยก secrets ออกจาก source code
