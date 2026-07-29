# Methodology and Reproducibility

## วัตถุประสงค์

การทดสอบนี้แยกคำถามห้าข้อออกจากกัน:

1. Structural chunk ที่สร้างมีมาตราที่ต้องใช้หรือไม่
2. Retriever นำมาตรานั้นเข้ามาใน candidate set หรือไม่
3. OpenThai reranker เลือกหลักฐานที่ใช้จริงได้หรือไม่
4. Generator อ้างเฉพาะหลักฐานที่ส่งให้หรือไม่
5. เนื้อคำตอบทางกฎหมายถูกต้องและไม่เกินหลักฐานหรือไม่

การรายงานแยกแต่ละชั้นทำให้ไม่สรุปผิดว่า “โมเดลตอบผิด” ในกรณีที่
retriever ไม่เคยส่งมาตราที่ถูกให้โมเดล หรือสรุปว่า “RAG ดี” เพียงเพราะ
มาตราที่ถูกอยู่ใน top-k แต่ generator เลือก near-miss

## สภาพแวดล้อม

- OpenThai endpoint: local vLLM OpenAI-compatible API
- Served context length: 32,768 tokens
- Embedding: Qwen3-Embedding-4B service
- Web/API service: port 8083
- Chat session store: PostgreSQL database `opengpt`
- Dense backend ใน live UI: Qdrant Local
- Lexical backends: Python BM25 และ SQLite FTS5 trigram

PID, credentials, GPU identifiers และ access token ไม่บันทึกใน repository

## Corpora

### NCB

ใช้ structural chunks 73 รายการจากพระราชบัญญัติการประกอบธุรกิจข้อมูล
เครดิต แบ่งตามมาตรา เก็บชื่อกฎหมาย เลขมาตรา หน้า และข้อความเดิม

### NitiBench

ใช้ local SQLite vector corpus ที่เตรียมจาก NitiBench:

- CCL: 3,833 records, 22 laws
- Tax: 101 records, 4 laws

retrieval profile benchmark สุ่ม 115 คำถามแบบกระจายตามกลุ่มกฎหมาย
ส่วน generation selection ใช้ 9 กรณีข้ามกฎหมาย

## Metrics

### Retrieval

- `Hit rate`: มี expected section อย่างน้อยหนึ่งรายการใน top-k
- `Macro section recall`: recall ของ expected sections เฉลี่ยรายคำถาม
- `MRR`: reciprocal rank ของ expected hit แรก
- `Mean/P95 latency`: เวลาค้นหลัง precompute embedding

### Citation

- `Citation recall`: จำนวน expected citations ที่ตอบ / จำนวน expected
- `Citation precision`: จำนวน citations ที่ถูก / citations ทั้งหมดที่ตอบ
- `Exact citation set`: recall และ precision เท่ากับ 1 พร้อมกัน
- `Grounded precision`: citation ที่ตอบต้องอยู่ใน supplied evidence

การ match ใช้ทั้ง `law_name` และเลข `section` เมื่อ dataset มีข้อมูลครบ
ไม่ใช้เฉพาะเลขมาตรา เพราะกฎหมายต่างฉบับอาจมีเลขซ้ำกัน

## Generation profiles

ค่าตาม model card:

```json
{
  "citation_rag": {
    "temperature": 0.0,
    "top_p": 1.0,
    "max_tokens": 2048,
    "thinking": false
  },
  "legal_essay": {
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 4096,
    "thinking": false
  },
  "legal_essay_thinking": {
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 6144,
    "thinking": true
  },
  "general_legal_chat": {
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 2048,
    "thinking": false
  },
  "closed_book": {
    "temperature": 0.0,
    "top_p": 1.0,
    "max_tokens": 2048,
    "thinking": false
  }
}
```

Citation answering ใช้ JSON citation contract จาก model card และ parse
JSON หลัง generation ไม่ใช้ constrained decoding เป็นตัวตัดสิน correctness

## Codex judge rubric

Codex อ่านผลหลัง deterministic metrics โดยใช้เกณฑ์:

1. ตอบประเด็นของ scenario ครบ
2. อ้างกฎหมายและมาตราตรง evidence
3. ไม่สร้างข้อเท็จจริง อำนาจ หรือขั้นตอนที่ evidence ไม่รองรับ
4. แยก allegation, investigation และ final adjudication
5. ระบุ evidence gap/ความไม่แน่นอนเมื่อจำเป็น
6. ภาษาและรูปแบบเหมาะกับ mode

Codex judge เป็นการประเมินเชิงคุณภาพ ไม่ใช่ independent legal expert
และไม่ใช้แทนการตรวจโดยนักกฎหมายหรือการตรวจ primary source

## ข้อจำกัด

- NCB focused generation มีเพียง 5 scenarios
- NitiBench generation selection มี 9 scenarios
- Essay มี 2 scenarios ต่อ profile จึงใช้ตัดสินแนวโน้ม ไม่ใช่ significance
- Vector backend smoke test ใช้ corpus 73 chunks และคำถามเดียว
- Retrieval latency ไม่รวม embedding และไม่เทียบ production concurrency
- ตัวอย่างข่าว/ground truth ที่ผู้ใช้ให้ต้องตรวจฉบับกฎหมายปัจจุบัน
- ไม่มีการอ้างว่า Docker standalone ผ่าน runtime เพราะ Docker daemon
  ไม่พร้อมในเครื่องทดสอบ

## วิธีรันซ้ำ

1. เริ่ม OpenThai vLLM และ embedding service
2. ตั้ง environment ของ corpus, PostgreSQL และ vector backend
3. เริ่ม `web/rag_webui_8083/server.py`
4. รัน benchmark scripts ใน `tools/advanced_rag/`
5. ตรวจ JSON ว่า `complete` เป็น `true`
6. ตรวจ health, Python compile และ Docker Compose configuration
7. ตรวจคำตอบเชิงคุณภาพโดยไม่แก้ ground truth หลังเห็นผล

รายละเอียด exact command ขึ้นกับ model path และ credential ของเครื่อง
จึงตั้งใจไม่ hard-code secret หรือ path ของผู้ใช้ใน repository
