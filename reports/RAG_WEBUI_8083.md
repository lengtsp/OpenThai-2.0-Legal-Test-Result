# OpenThai Legal RAG Workbench (port 8083)

เปิดที่ `http://localhost:8083` โดย service แยกจากหน้าเดิมที่ port 3001 และเรียก OpenAI-compatible vLLM ที่ `127.0.0.1:3033`.

## การทำงาน

1. เพิ่มข้อความกฎหมายทีละมาตรา/ข้อ พร้อมชื่อเอกสารและเลขมาตรา
2. ระบบค้นด้วย BM25 แบบ lexical พร้อม Thai character trigrams เพื่อรองรับข้อความไทยที่ไม่มีเว้นวรรค
3. ส่ง top-k evidence chunks ให้ OpenThai2.0 Legal พร้อมคำสั่งให้อ้างได้เฉพาะหลักฐานที่ส่ง
4. ใต้คำตอบจะแสดง latency ค้นคืน, latency inference, token usage และข้อความหลักฐานฉบับเต็ม

แนวทางนี้ยึดหลักจากโปรเจ็กต์ RAG ต้นทาง: รักษา raw evidence, แยก chunk ตาม section, เก็บ source/section, และทำให้ citation ตรวจสอบย้อนกลับได้. ไม่ได้เชื่อม `/api/prod/*` ของโปรเจ็กต์ต้นทาง เพราะ API นั้นต้องมีสิทธิ์/credential และบริการต้นทางไม่ได้เปิดในเครื่องนี้.

## Endpoints

- `GET /api/health` ตรวจ vLLM และจำนวน evidence
- `GET /api/corpus` อ่านคลังหลักฐาน
- `POST /api/corpus` เพิ่ม `{law_name, section, content}`
- `POST /api/retrieve` ทดสอบ retrieval ด้วย `{query, top_k}`
- `POST /api/chat` ค้นหลักฐานและเรียก vLLM ในคำขอเดียว

ข้อมูล evidence เก็บใน `rag_webui_8083/data/legal_corpus.json` และมีปุ่มเพิ่มชุดทดสอบขนาดเล็กสำหรับตรวจ workflow เท่านั้น.

## Chat session persistence (PostgreSQL)

Database `opengpt` บน `127.0.0.1:5432` เก็บการสนทนาของหน้า RAG โดยมีตาราง:

- `chat_sessions`: UUID, ชื่อ session, เวลาเริ่มและใช้งานล่าสุด
- `chat_messages`: user/assistant content, reasoning, RAG citations, token usage และ timing ต่อ turn

หน้าเว็บจำ session UUID ไว้ใน browser local storage; เมื่อเปิดหรือรีเฟรชหน้าเดิม ระบบจะอ่านประวัติจาก PostgreSQL กลับมาอัตโนมัติ. ปุ่ม `แชตใหม่` จะเริ่ม session ใหม่ โดยไม่ลบประวัติเดิม.

RAG service อ่าน credential ผ่าน environment variables `OPENGPT_DB_HOST`, `OPENGPT_DB_PORT`, `OPENGPT_DB_NAME`, `OPENGPT_DB_USER` และ `OPENGPT_DB_PASSWORD`; credential ไม่ได้ฝังไว้ใน source code.

## ผลทดสอบเมื่อเปิดบริการ

- vLLM health: ready (`openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b`)
- คำถาม: “บุคคลทำให้ทรัพย์สินผู้อื่นเสียหายโดยประมาท ต้องรับผิดอย่างไร”
- retrieval top-1: ประมวลกฎหมายแพ่งและพาณิชย์ (ตัวอย่าง) มาตรา 420
- คำตอบอ้าง `[1]` เฉพาะมาตรา 420 แม้ส่ง distractor มาตรา 328 และ 335 เข้า selection pool
- เวลา retrieval 0.6 ms, vLLM generation 12.0 s, prompt 627 tokens, output 225 tokens
