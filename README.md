# OpenThai 2.0 Legal — PostgreSQL vs Milvus RAG

Repository นี้เก็บผลทดสอบอิสระของ
[`OpenThai 2.0 Legal`](https://huggingface.co/iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b)
ซึ่งพัฒนาโดย iApp Technology และรันผ่าน vLLM แบบ OpenAI-compatible
บนเครื่อง local ผู้จัดทำเป็นผู้ทดสอบ ไม่ใช่ผู้พัฒนา ผู้แทน หรือผู้รับรองโมเดล

README ฉบับนี้รายงานเฉพาะ **Citation RAG** โดยเปรียบเทียบ PostgreSQL กับ
Milvus บนคำถามและ ground truth ชุดเดียวกัน ส่วน Closed-book และ Legal essay
ยังไม่นำมาสรุปเป็นผลด้านความถูกต้อง เนื่องจากต้องให้ผู้เชี่ยวชาญกฎหมายตรวจ
คำวินิจฉัย เนื้อหามาตรา กฎหมายลำดับรอง และข้อยกเว้นเพิ่มเติม

> ผลนี้เป็นการประเมินระบบช่วยค้นและตอบ ไม่ใช่คำแนะนำหรือคำวินิจฉัยทางกฎหมาย

## สรุปสั้น

ในการทดสอบ NitiBench 5 ข้อ:

- PostgreSQL และ Milvus ค้น expected section ได้อันดับ 1 ครบ 5/5
- candidate recall@20, rerank recall, citation recall และ citation precision
  เท่ากับ 100% ทั้งสอง backend
- คำตอบสุดท้ายและ citation เหมือนกันครบ 5/5 ข้อ
- Milvus ใช้ retrieval pipeline เฉลี่ย 0.057 วินาที เทียบกับ PostgreSQL
  1.630 วินาทีในรอบที่บันทึกไว้
- เวลา end-to-end เฉลี่ยลดจาก 9.16 เป็น 7.28 วินาที หรือลดลงประมาณ 20.5%

ดังนั้น ใน sample นี้ **คุณภาพคำตอบเสมอกัน แต่ Milvus เร็วกว่าใน retrieval
stage อย่างชัดเจน** อย่างไรก็ตาม ผลเวลาเป็นคนละรอบการรันและได้รับอิทธิพลจาก
warm-up, cache และภาระของเครื่อง จึงไม่ควรตีความเป็น production load
benchmark

## ชุดข้อมูล

ใช้ [`VISAI-AI/NitiBench`](https://huggingface.co/datasets/VISAI-AI/nitibench)
ซึ่งเตรียมเป็น structural legal chunks จำนวน 3,934 รายการ:

- CCL 3,833 chunks
- Tax 101 chunks
- หนึ่งบทบัญญัติต่อหนึ่ง record
- metadata หลักคือ `law_name`, `section_num` และ `content`
- dense embedding 2,560 มิติจาก Qwen3-Embedding-4B GGUF Q4
- ไม่รวม `answer` หรือ `reference_answer` ในข้อความที่นำไปสร้าง passage
  embedding

Expected answer และ expected law/section ใช้เฉพาะหลัง inference เพื่อให้คะแนน
ไม่ได้ส่งให้ embedding model, retriever, OpenThai reranker หรือ final answer
เห็นล่วงหน้า

## Pipeline ที่เปรียบเทียบ

### PostgreSQL

```text
Question
  ├─ Dense: Qwen3-Embedding-4B + pgvector/halfvec cosine
  └─ Sparse: PostgreSQL tsvector + pg_trgm
          ↓
      Application RRF k=60
          ↓
        top_k=20
          ↓
  OpenThai evidence selection
          ↓
  OpenThai citation answer
```

ข้อมูลอยู่ใน PostgreSQL database `openthai` โดยแยก legal chunks และ embedding
ออกเป็นตารางที่เชื่อมด้วย `chunk_id`

### Milvus

```text
Question
  ├─ Dense: Qwen3-Embedding-4B + Milvus cosine
  └─ Sparse: Milvus BM25 บน Thai 3/4-character n-grams
          ↓
      Milvus native RRF k=80
          ↓
        top_k=20
          ↓
  OpenThai evidence selection
          ↓
  OpenThai citation answer
```

Milvus collection ชื่อ `nitibench_legal_v2_rrf` มี 3,934 records พร้อม
`dense_vector`, `sparse_thai`, `law_name`, `section_num` และ `content`

การเปรียบเทียบนี้เป็นการเทียบ **pipeline ที่ปรับให้เหมาะกับแต่ละ backend**
ไม่ใช่การควบคุมให้ sparse index และค่า RRF เหมือนกันทุกประการ

## Generation settings

OpenThai ใช้ค่าเดียวกันทั้งตอนคัดเลือก evidence และสร้างคำตอบ:

| Parameter | Value |
|---|---:|
| temperature | 0.0 |
| top_p | 1.0 |
| max_tokens | 2,048 |
| thinking | off |
| seed | 42 |
| vLLM context window | 32,768 |
| retrieved candidates | 20 |

การเปลี่ยน generation parameters ทำที่ request ได้ ไม่ต้อง restart vLLM
ส่วน model ถูก unload หลังจบการทดสอบแล้ว จึงไม่มีการใช้ VRAM ต่อเนื่อง

## ผลเปรียบเทียบภาพรวม

| Metric | PostgreSQL | Milvus |
|---|---:|---:|
| จำนวนคำถาม | 5 | 5 |
| Expected section อยู่ rank 1 | 5/5 | 5/5 |
| Candidate recall@20 | 100% | 100% |
| Rerank recall | 100% | 100% |
| Citation recall | 100% | 100% |
| Citation precision | 100% | 100% |
| Exact citation set | 5/5 | 5/5 |
| Valid final JSON | 5/5 | 5/5 |
| คำตอบเหมือนกันระหว่าง backend | 5/5 | 5/5 |
| Backend search เฉลี่ย | 1.386 วินาที | 0.013 วินาที |
| Retrieval รวม embedding เฉลี่ย | 1.630 วินาที | 0.057 วินาที |
| End-to-end เฉลี่ย | 9.156 วินาที | 7.280 วินาที |
| LLM tokens รวม | 39,164 | 30,189 |

จากค่าที่บันทึกไว้ Milvus เร็วกว่าใน retrieval pipeline ประมาณ 28.6 เท่า
และ backend search อย่างเดียวประมาณ 106 เท่า แต่ตัวเลขนี้รวมผลของ cache และ
warm-up ในการรันคนละช่วงเวลา ไม่ใช่ผลจาก concurrent load test

จำนวน token ของ Milvus ต่ำกว่าประมาณ 22.9% เพราะ candidate packet ที่ได้จาก
แต่ละ backend มีข้อความและลำดับไม่เหมือนกันทั้งหมด ไม่ควรสรุปว่าเปลี่ยน
database แล้ว token จะลดลงในทุก corpus

## ผลรายข้อและไฟล์คำตอบเต็ม

| # | คำถาม | Expected citation | PostgreSQL | Milvus |
|---:|---|---|---|---|
| 1 | ประกอบกิจการศูนย์ซื้อขายสัญญาซื้อขายล่วงหน้าโดยไม่มีใบอนุญาตมีโทษอย่างไร | พ.ร.บ. สัญญาซื้อขายล่วงหน้า มาตรา 132 | [TXT](results/rag-postgresql-vs-milvus-20260730/postgresql/rag-01-99fb5f5a.txt) | [TXT](results/rag-postgresql-vs-milvus-20260730/milvus/rag-01-99fb5f5a.txt) |
| 2 | การเช่าถือสวนมีระยะเวลากี่ปี | ป.พ.พ. มาตรา 565 | [TXT](results/rag-postgresql-vs-milvus-20260730/postgresql/rag-02-f781c322.txt) | [TXT](results/rag-postgresql-vs-milvus-20260730/milvus/rag-02-f781c322.txt) |
| 3 | ผู้เยาว์เป็นบุตรบุญธรรมของหลายคนพร้อมกันได้หรือไม่ | ป.พ.พ. มาตรา 1598/26 | [TXT](results/rag-postgresql-vs-milvus-20260730/postgresql/rag-03-0db37f05.txt) | [TXT](results/rag-postgresql-vs-milvus-20260730/milvus/rag-03-0db37f05.txt) |
| 4 | สัญญาบัญชีเดินสะพัดคืออะไร | ป.พ.พ. มาตรา 856 | [TXT](results/rag-postgresql-vs-milvus-20260730/postgresql/rag-04-a488029b.txt) | [TXT](results/rag-postgresql-vs-milvus-20260730/milvus/rag-04-a488029b.txt) |
| 5 | ผู้ถือหุ้นในบริษัทจำกัดรับผิดอย่างไร | ป.พ.พ. มาตรา 1096 | [TXT](results/rag-postgresql-vs-milvus-20260730/postgresql/rag-05-c9f3cc21.txt) | [TXT](results/rag-postgresql-vs-milvus-20260730/milvus/rag-05-c9f3cc21.txt) |

ไฟล์ TXT แต่ละไฟล์เก็บ:

- system prompt และ user question
- embedding request metadata
- candidate top 20 พร้อมข้อความกฎหมาย
- ผล OpenThai evidence selection
- final answer และ citation
- เวลาในแต่ละ stage
- prompt/completion/total token usage
- evaluation หลัง inference

## ตัวอย่างคำตอบที่ได้เหมือนกัน

คำถาม:

> ถ้ามีคนประกอบกิจการในลักษณะเป็นศูนย์ซื้อขายสัญญาซื้อขายล่วงหน้า
> โดยไม่ได้รับใบอนุญาตต้องระวางโทษอย่างไร

คำตอบจาก PostgreSQL และ Milvus:

> ผู้ใดประกอบกิจการในลักษณะเป็นศูนย์ซื้อขายสัญญาซื้อขายล่วงหน้า
> โดยไม่ได้รับใบอนุญาตหรือไม่ได้จดทะเบียน ต้องระวางโทษจำคุกไม่เกินสามปี
> หรือปรับไม่เกินสามแสนบาท หรือทั้งจำทั้งปรับ และปรับอีกไม่เกินวันละ
> หนึ่งหมื่นบาทตลอดเวลาที่ยังฝ่าฝืน

```json
{
  "citations": [
    {
      "law": "พระราชบัญญัติสัญญาซื้อขายล่วงหน้า พ.ศ. 2546",
      "section": "132"
    }
  ]
}
```

## ข้อสรุปเชิงระบบ

สำหรับ corpus ขนาด 3,934 chunks และคำถามชุดนี้:

1. PostgreSQL เพียงพอด้านคุณภาพและดูแลง่าย หากมี PostgreSQL อยู่แล้วและ
   ปริมาณข้อมูล/traffic ยังไม่สูง
2. Milvus ให้คุณภาพเท่ากันใน 5 ตัวอย่าง แต่ retrieval latency ต่ำกว่า
   เหมาะกับการขยายจำนวน vector, query throughput หรือ native hybrid search
3. คอขวดของ Milvus pipeline ไม่ใช่ vector search แต่เป็น LLM rerank และ
   generation ซึ่งใช้เวลาส่วนใหญ่ของ 7.28 วินาที
4. แนวทางลด latency/cost ต่อไปควรทดลองลด rerank packet, adaptive top_k หรือ
   dedicated reranker โดยต้องรักษา citation recall
5. ก่อนใช้จริงต้องทดสอบคำถามหลายมาตรา, near-miss statutes, กฎหมายชื่อคล้ายกัน,
   อนุมาตรา และ corpus ที่ใหญ่กว่าเดิม

## ขอบเขตและข้อจำกัด

- มีเพียง 5 คำถาม และแต่ละข้อมี expected section หลักเพียงหนึ่งมาตรา
- เป็น paired functional benchmark ไม่ใช่ stress/concurrency benchmark
- PostgreSQL และ Milvus ใช้ sparse retrieval/fusion configuration ต่างกัน
- Citation ตรง ground truth ไม่ได้หมายความว่าคำตอบเป็นคำวินิจฉัยทางกฎหมาย
- การใช้ในงานจริงต้องตรวจตัวบทฉบับปัจจุบัน ข้อเท็จจริง ข้อยกเว้น และ
  กฎหมายลำดับรองโดยผู้เชี่ยวชาญ

Repository นี้ไม่เก็บ model weights, database credentials, access token หรือ
chat sessions
