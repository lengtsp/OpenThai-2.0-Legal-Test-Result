# ทดสอบ OpenThai 2.0 Legal — Three-mode benchmark

Repository นี้บันทึกผลทดสอบอิสระของ
[`OpenThai 2.0 Legal`](https://huggingface.co/iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b)
ซึ่งพัฒนาโดย iApp Technology บนฐาน NVIDIA Nemotron-3-Nano-30B-A3B
และรันแบบ self-hosted ผ่าน vLLM ผู้จัดทำ repository เป็นผู้ทดสอบ
ไม่ใช่ผู้พัฒนา ผู้แทน หรือผู้รับรองโมเดล

โมเดลนี้ออกแบบมาสำหรับความรู้กฎหมายไทยและการอ้างอิงระดับมาตรา
โดย model card รองรับทั้ง Open-book/RAG, Closed-book และ Legal essay
ส่วนชุดข้อมูล
[`VISAI-AI/NitiBench`](https://huggingface.co/datasets/VISAI-AI/nitibench)
ออกแบบเพื่อประเมินระบบตอบคำถามกฎหมายไทย เช่น RAG และ LCLM
พร้อมคำถาม คำตอบ และตัวบทกฎหมายที่ใช้อ้างอิง

> ผลทั้งหมดเป็นการประเมินระบบช่วยค้นและตอบ ไม่ใช่คำแนะนำหรือ
> คำวินิจฉัยทางกฎหมาย ก่อนใช้งานจริงต้องตรวจตัวบทฉบับปัจจุบัน
> ข้อเท็จจริง และคำตอบโดยผู้เชี่ยวชาญ

## ขอบเขตการทดสอบ

ทดสอบ 3 modes รวม **12 unique scenarios** และมี raw TXT **17 ไฟล์**
เพราะ RAG 5 ข้อถูกรันกับ retrieval backend สองแบบ

| Mode | Unique scenarios | Backend runs | TXT files | สถานะการประเมิน |
|---|---:|---:|---:|---|
| Citation RAG | 5 | PostgreSQL + Milvus | 10 | ประเมินกับ NitiBench ground truth |
| Legal essay | 2 | Retrieval-free 1 รอบ | 2 | เปรียบเทียบกับ test reference; รอผู้เชี่ยวชาญยืนยัน |
| Closed-book | 5 | Retrieval-free 1 รอบ | 5 | ตรวจรูปแบบ/มาตราเบื้องต้น; รอผู้เชี่ยวชาญยืนยัน |
| **รวม** | **12** | — | **17** | — |

- [RAG ผ่าน PostgreSQL 5 ไฟล์](results/rag-postgresql-vs-milvus-20260730/postgresql/)
- [RAG ผ่าน Milvus 5 ไฟล์](results/rag-postgresql-vs-milvus-20260730/milvus/)
- [Legal essay 2 ไฟล์](results/three-mode-raw-20260730/legal_essay/)
- [Closed-book 5 ไฟล์](results/three-mode-raw-20260730/closed_book/)

## สิ่งที่ model card รองรับ

Model card แยกงานที่เกี่ยวข้องกับการทดสอบนี้ไว้ชัดเจน:

| Mode | สิ่งที่ทดสอบ | Evidence ใน prompt |
|---|---|---|
| Open-book echo | ใช้เอกสารที่เกี่ยวข้องทั้งหมด | มีเฉพาะมาตราที่ถูก |
| Open-book selection | เลือกมาตราที่ใช้จริงและตัด near-miss | มีทั้งมาตราที่เกี่ยวข้องและ distractors |
| Closed-book | ความจำกฎหมายจาก model weights | ไม่มีตัวบท |
| Legal essay | การเขียนวิเคราะห์ยาว การอ้างมาตรา holding coverage และ fluency | โจทย์คดี |

RAG ใน repository นี้ใกล้กับ **Open-book selection** เพราะ retriever ส่ง
candidate 20 รายการให้ OpenThai เลือก evidence ก่อนตอบ

## Requirements และสภาพแวดล้อม

| Component | ค่าที่ใช้ |
|---|---|
| Generator | OpenThai 2.0 Legal ผ่าน vLLM/OpenAI-compatible API |
| Served context window | 32,768 tokens รวม prompt + completion |
| Embedding | Qwen3-Embedding-4B GGUF Q4 |
| Embedding dimensions | 2,560 |
| Primary vector store | PostgreSQL + pgvector |
| Backend ที่นำมาเปรียบเทียบ | Milvus Standalone |
| RAG candidate count | `top_k=20` |
| Corpus | VISAI-AI/NitiBench |

OpenThai vLLM ถูก unload หลังจบการทดสอบแล้ว ผลที่เผยแพร่เป็น artifacts
จาก inference ที่รันเสร็จสมบูรณ์ ไม่ได้สร้างขึ้นใหม่ภายหลัง

## การเตรียม NitiBench ใน PostgreSQL

NitiBench มี fields หลัก:

- `question`
- `answer`
- `relevant_laws`
- `reference_answer`
- `reference_laws`

การสร้าง passage embedding **ไม่รวม `answer` หรือ `reference_answer`**
โดยนำข้อมูลกฎหมายมาสร้าง `embedding_text` ดังนี้:

```text
กฎหมาย: {law_name}
มาตรา: {section_num}
ข้อความบทบัญญัติ:
{section_body_without_repeated_heading}
```

ตัวอย่างจริง:

```text
กฎหมาย: ประมวลกฎหมายแพ่งและพาณิชย์
มาตรา: 1096
ข้อความบทบัญญัติ:
อันว่าบริษัทจำกัดนั้น คือบริษัทประเภทซึ่งตั้งขึ้นด้วยแบ่งทุนเป็นหุ้น
มีมูลค่าเท่า ๆ กัน โดยผู้ถือหุ้นต่างรับผิดจำกัดเพียงไม่เกินจำนวนเงิน
ที่ตนยังส่งใช้ไม่ครบมูลค่าของหุ้นที่ตนถือ
```

Schema ที่ใช้:

| Table | จำนวน | หน้าที่ |
|---|---:|---|
| `benchmark_cases` | 3,779 | คำถาม คำตอบ และ source payload |
| `benchmark_case_laws` | 7,008 | ความสัมพันธ์ case → relevant/reference law |
| `legal_chunks` | 3,934 | หนึ่งบทบัญญัติต่อหนึ่ง record พร้อม metadata/FTS |
| `legal_chunk_embeddings` | 3,934 | passage embedding profile `qwen3-legal-v2` |
| `benchmark_query_embeddings` | 3,779 | query embedding สำหรับ benchmark |

Embedding แยกจาก legal chunk ด้วย `chunk_id` เพื่อให้สร้าง embedding profile
ใหม่ได้โดยไม่แก้ข้อความกฎหมาย และเก็บ `embedding_text`/`input_hash`
สำหรับตรวจสอบย้อนหลัง

## Hybrid RAG

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
  OpenThai evidence selection/rerank
          ↓
  Focused statutory context
          ↓
  OpenThai citation answer
```

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
  OpenThai evidence selection/rerank
          ↓
  Focused statutory context
          ↓
  OpenThai citation answer
```

Milvus collection `nitibench_legal_v2_rrf` มี 3,934 records พร้อม
`dense_vector`, `sparse_thai`, `law_name`, `section_num` และ `content`

การเปรียบเทียบนี้เป็นการเทียบ **pipeline ที่ปรับให้เหมาะกับแต่ละ backend**
ไม่ใช่การควบคุม sparse index และ RRF ให้เหมือนกันทุกประการ

## Generation settings

ค่าที่แนะนำใน model card:

| Use case | temperature | top_p | max_tokens | thinking |
|---|---:|---:|---:|---|
| Citation answering — RAG/Closed-book | 0.0 | 1.0 | 2,048 | off |
| Legal essay drafting | 0.7 | 0.9 | 4,096 | on หรือ off |
| Legal essay with thinking | 0.7 | 0.9 | 6,144 | on |
| General chat | 0.7 | 0.9 | 2,048 | off |

ค่าที่ใช้จริง:

| Mode/Stage | temperature | top_p | max_tokens | thinking | seed |
|---|---:|---:|---:|---|---:|
| RAG retrieval rerank | 0.0 | 1.0 | 2,048 | off | 42 |
| RAG final citation answer | 0.0 | 1.0 | 2,048 | off | 42 |
| Closed-book | 0.0 | 1.0 | 2,048 | off | 42 |
| Legal essay | 0.7 | 0.9 | 4,096 | off | 42 |

Model card ระบุว่า `max_tokens` เป็น per-request setting ไม่ใช่ model limit
และแนะนำ context window 32,768 เนื่องจาก prompt กฎหมาย/ภาษีอาจยาว
การเปลี่ยน generation parameters ทำที่ request ได้ ไม่ต้อง restart vLLM

## ผลเปรียบเทียบภาพรวม

| Mode | จำนวน | ผลเชิงระบบ | เวลาเฉลี่ย | Tokens รวม | ข้อสรุป |
|---|---:|---|---:|---:|---|
| RAG/PostgreSQL | 5 | expected section rank 1 และ citation ถูก 5/5 | 9.156s | 39,164 | ผ่านชุดตัวอย่าง |
| RAG/Milvus | 5 | expected section rank 1 และ citation ถูก 5/5 | 7.280s | 30,189 | ผ่านชุดตัวอย่าง |
| Legal essay | 2 | ตอบจบ 2/2; keyword checklist เฉลี่ย 40% | 30.816s | 2,803 | holding ขัด test reference ทั้ง 2 ข้อ; รอผู้เชี่ยวชาญ |
| Closed-book | 5 | valid JSON 5/5; expected-section macro recall 50% | 5.881s | 3,035 | ตรวจเบื้องต้นเท่านั้น; รอผู้เชี่ยวชาญ |

ตัวเลข Legal essay และ Closed-book ไม่ใช่คะแนนรับรองความถูกต้องทางกฎหมาย
เพราะ test references ไม่ได้ผ่าน legal-expert adjudication ในรอบนี้

# Mode 1 — Citation RAG

## การเลือกคำถาม

ใช้คำถามจาก NitiBench ต้นฉบับ 5 ข้อ และตรึงคำถามชุดเดียวกันสำหรับ
PostgreSQL/Milvus paired comparison

คำขอเดิมใช้คำว่า “สุ่ม 5 ข้อ” แต่ runner ที่เก็บ artifact ใช้ fixed list
โดยไม่มี random seed สำหรับขั้น sampling ดังนั้นรายงานนี้ไม่อ้างว่าเป็น
auditable random sample

Expected `relevant_laws` ใช้ให้คะแนนหลังตอบเท่านั้น ไม่ส่งเข้า embedding,
retrieval, reranker หรือ final answer ล่วงหน้า

## ผล PostgreSQL เทียบ Milvus

| Metric | PostgreSQL | Milvus |
|---|---:|---:|
| Expected section อยู่ rank 1 | 5/5 | 5/5 |
| Candidate recall@20 | 100% | 100% |
| Rerank recall | 100% | 100% |
| Citation recall | 100% | 100% |
| Citation precision | 100% | 100% |
| Exact citation set | 5/5 | 5/5 |
| Valid final JSON | 5/5 | 5/5 |
| คำตอบเหมือนกันระหว่าง backend | 5/5 | 5/5 |
| Backend search เฉลี่ย | 1.386s | 0.013s |
| Retrieval รวม embedding เฉลี่ย | 1.630s | 0.057s |
| End-to-end เฉลี่ย | 9.156s | 7.280s |
| LLM tokens รวม | 39,164 | 30,189 |

Milvus เร็วกว่าใน retrieval pipeline ที่บันทึกไว้ประมาณ 28.6 เท่า
และ end-to-end ลดลงประมาณ 20.5% แต่เป็นคนละรอบเวลา/cache
ไม่ใช่ stress หรือ concurrency benchmark

### RAG 1 — ศูนย์ซื้อขายสัญญาซื้อขายล่วงหน้าไม่มีใบอนุญาต

<details>
<summary>กดเพื่อดูคำถาม, selected context และคำตอบ</summary>

**คำถาม**

> ถ้ามีคนประกอบกิจการในลักษณะเป็นศูนย์ซื้อขายสัญญาซื้อขายล่วงหน้า
> โดยไม่ได้รับใบอนุญาตต้องระวางโทษอย่างไร

**Selected context**

```xml
<law law_name="พระราชบัญญัติสัญญาซื้อขายล่วงหน้า พ.ศ. 2546" section="132">
ผู้ใดประกอบกิจการในลักษณะเป็นศูนย์ซื้อขายสัญญาซื้อขายล่วงหน้า
โดยไม่ได้รับใบอนุญาตหรือไม่ได้จดทะเบียนตามมาตรา 54
ต้องระวางโทษจำคุกไม่เกินสามปี หรือปรับไม่เกินสามแสนบาท
หรือทั้งจำทั้งปรับ และปรับอีกไม่เกินวันละหนึ่งหมื่นบาท
ตลอดเวลาที่ยังฝ่าฝืน
</law>
```

**คำตอบจาก OpenThai**

```json
{
  "answer": "ผู้ใดประกอบกิจการในลักษณะเป็นศูนย์ซื้อขายสัญญาซื้อขายล่วงหน้าโดยไม่ได้รับใบอนุญาตหรือไม่ได้จดทะเบียน ต้องระวางโทษจำคุกไม่เกินสามปี หรือปรับไม่เกินสามแสนบาท หรือทั้งจำทั้งปรับ และปรับอีกไม่เกินวันละหนึ่งหมื่นบาทตลอดเวลาที่ยังฝ่าฝืน",
  "citations": [
    {
      "law": "พระราชบัญญัติสัญญาซื้อขายล่วงหน้า พ.ศ. 2546",
      "section": "132"
    }
  ]
}
```

**Artifacts:** [PostgreSQL](results/rag-postgresql-vs-milvus-20260730/postgresql/rag-01-99fb5f5a.txt) · [Milvus](results/rag-postgresql-vs-milvus-20260730/milvus/rag-01-99fb5f5a.txt)

</details>

### RAG 2 — การเช่าถือสวน

<details>
<summary>กดเพื่อดูคำถามและคำตอบ</summary>

**คำถาม**

> การเช่าถือสวนมีระยะเวลากี่ปี

**Expected/selected law:** ประมวลกฎหมายแพ่งและพาณิชย์ มาตรา 565

```json
{
  "answer": "การเช่าถือสวนมีระยะเวลากันปีหนึ่ง",
  "citations": [
    {
      "law": "ประมวลกฎหมายแพ่งและพาณิชย์",
      "section": "565"
    }
  ]
}
```

**Artifacts:** [PostgreSQL](results/rag-postgresql-vs-milvus-20260730/postgresql/rag-02-f781c322.txt) · [Milvus](results/rag-postgresql-vs-milvus-20260730/milvus/rag-02-f781c322.txt)

</details>

### RAG 3 — ผู้เยาว์เป็นบุตรบุญธรรมหลายคนพร้อมกัน

<details>
<summary>กดเพื่อดูคำถามและคำตอบ</summary>

**คำถาม**

> ผู้เยาว์สามารถเป็นบุตรบุญธรรมของคนหลายคนในเวลาเดียวกันได้หรือไม่

**Expected/selected law:** ประมวลกฎหมายแพ่งและพาณิชย์ มาตรา 1598/26

```json
{
  "answer": "ผู้เยาว์ไม่สามารถเป็นบุตรบุญธรรมของคนหลายคนในเวลาเดียวกันได้ เว้นแต่เป็นบุตรบุญธรรมของคู่สมรสของผู้รับบุตรบุญธรรม",
  "citations": [
    {
      "law": "ประมวลกฎหมายแพ่งและพาณิชย์",
      "section": "1598/26"
    }
  ]
}
```

รอบ Milvus แรก reranker เลือก `C01` ถูกต้องแต่ JSON ขาดวงเล็บปิด
ระบบจึงใช้ generic syntax recovery ซึ่งยอมรับเฉพาะ ID ที่ model
เขียนไว้ใน `selected_ids` และมีอยู่จริงใน candidate set
ไม่มีการ hardcode เลขมาตราหรือ ground truth

**Artifacts:** [PostgreSQL](results/rag-postgresql-vs-milvus-20260730/postgresql/rag-03-0db37f05.txt) · [Milvus](results/rag-postgresql-vs-milvus-20260730/milvus/rag-03-0db37f05.txt)

</details>

### RAG 4 — สัญญาบัญชีเดินสะพัด

<details>
<summary>กดเพื่อดูคำถามและคำตอบ</summary>

**คำถาม**

> สัญญาบัญชีเดินสะพัดคืออะไร

**Expected/selected law:** ประมวลกฎหมายแพ่งและพาณิชย์ มาตรา 856

```json
{
  "answer": "สัญญาบัญชีเดินสะพัด คือ สัญญาซึ่งบุคคลสองคนตกลงกันว่าสืบแต่นั้นไป หรือในชั่วเวลากำหนดอันใดอันหนึ่ง ให้ตัดทอนบัญชีหนี้ทั้งหมดหรือแต่บางส่วนอันเกิดขึ้นแต่กิจการในระหว่างเขาทั้งสองนั้นหักกลบลบกัน และคงชำระแต่ส่วนที่เป็นจำนวนคงเหลือโดยดุลภาค",
  "citations": [
    {
      "law": "ประมวลกฎหมายแพ่งและพาณิชย์",
      "section": "856"
    }
  ]
}
```

**Artifacts:** [PostgreSQL](results/rag-postgresql-vs-milvus-20260730/postgresql/rag-04-a488029b.txt) · [Milvus](results/rag-postgresql-vs-milvus-20260730/milvus/rag-04-a488029b.txt)

</details>

### RAG 5 — ความรับผิดของผู้ถือหุ้นบริษัทจำกัด

<details>
<summary>กดเพื่อดูคำถามและคำตอบ</summary>

**คำถาม**

> ผู้ถือหุ้นในบริษัทจำกัด รับผิดในหุ้นอย่างไร

**Expected/selected law:** ประมวลกฎหมายแพ่งและพาณิชย์ มาตรา 1096

```json
{
  "answer": "ผู้ถือหุ้นในบริษัทจำกัดรับผิดจำกัดเพียงไม่เกินจำนวนเงินที่ตนยังส่งใช้ไม่ครบมูลค่าของหุ้นที่ตนถือ",
  "citations": [
    {
      "law": "ประมวลกฎหมายแพ่งและพาณิชย์",
      "section": "1096"
    }
  ]
}
```

**Artifacts:** [PostgreSQL](results/rag-postgresql-vs-milvus-20260730/postgresql/rag-05-c9f3cc21.txt) · [Milvus](results/rag-postgresql-vs-milvus-20260730/milvus/rag-05-c9f3cc21.txt)

</details>

# Mode 2 — Legal essay

System prompt:

```python
SYSTEM = "You are a Thai legal expert. Answer the question with legal analysis and cite the relevant มาตรา."
```

โจทย์และ test reference สร้างขึ้นเพื่อการทดลองโดย ChatGPT 5.6 sol
ไม่ได้มาจาก NitiBench และไม่ได้ผ่านการรับรองโดยผู้เชี่ยวชาญกฎหมาย
จึงรายงาน model output และความสอดคล้องเบื้องต้นเท่านั้น

## Legal essay 1 — ยักยอกกับใช้เอกสารสิทธิปลอม

<details>
<summary>กดเพื่อดูโจทย์ฉบับเต็ม</summary>

จำเลยเป็นพนักงานเก็บเงินของบริษัท มีหน้าที่เก็บเงินค่าสินค้าจากลูกค้า
และนำส่งเข้าบัญชีของบริษัทภายในวันทำการถัดไป จำเลยรับเงินจากลูกค้ารายหนึ่ง
จำนวน 120,000 บาท แล้วเบียดบังเงินดังกล่าวไปใช้เป็นประโยชน์ส่วนตัว
จำเลยจัดทำต้นฉบับใบเสร็จรับเงินปลอมในนามบริษัทมอบให้แก่ลูกค้า
และนำสำเนาใบเสร็จดังกล่าวไปใช้ประกอบรายงานการรับชำระเงิน
เพื่อให้บริษัทเข้าใจว่าจำเลยได้ดำเนินการเกี่ยวกับเงินที่รับจากลูกค้า
โดยถูกต้องแล้ว

ศาลชั้นต้นพิพากษาว่าจำเลยมีความผิดฐานยักยอกทรัพย์และฐานใช้
เอกสารสิทธิปลอม โดยเห็นว่าเป็นความผิดหลายกรรมต่างกันและให้ลงโทษทุกกรรม
เป็นกระทงความผิดไป จำเลยอุทธรณ์และฎีกาว่า การใช้ใบเสร็จรับเงินปลอม
เป็นส่วนหนึ่งของแผนการยักยอกเงินและมีเจตนามุ่งหมายเดียวกัน
จึงเป็นกรรมเดียวผิดกฎหมายหลายบทตามประมวลกฎหมายอาญา มาตรา 90

</details>

<details>
<summary>กดเพื่อดู test reference ที่ใช้เปรียบเทียบ</summary>

Test reference วางหลักว่า การปลอม/ใช้ใบเสร็จเป็นส่วนหนึ่งของแผนยักยอก
และมีวัตถุประสงค์เดียวกัน จึงเป็นกรรมเดียวผิดกฎหมายหลายบทตามมาตรา 90
ไม่ใช่หลายกรรมตามมาตรา 91 ผู้ปลอมและใช้เอกสารเองให้ลงโทษฐานใช้
ตามมาตรา 268 วรรคสอง ประกอบมาตรา 265 และให้ลงโทษบทหนักที่สุด

Reference ยังแยกกรณีที่การปลอมภายหลังมีวัตถุประสงค์ใหม่และเป็นอิสระ
ซึ่งอาจถือเป็นหลายกรรมได้

</details>

<details>
<summary>กดเพื่อดูคำตอบจริงจาก OpenThai</summary>

โมเดลวินิจฉัยว่าเป็นความผิดหลายกรรมต่างกันและต้องรับโทษทุกกรรม
เป็นกระทง โดยอ้างมาตรา 352 และมาตรา 268 พร้อมอธิบายว่าการยักยอกเงิน
กับการใช้เอกสารปลอมเป็นการกระทำสองส่วนที่แยกจากกัน

โมเดลยังกล่าวว่า:

> ประมวลกฎหมายอาญา มาตรา 90 กำหนดว่า หากบุคคลกระทำความผิดหลายกรรม
> ต่างกัน ให้ลงโทษทุกกรรมเป็นกระทงความผิดไป ... การยักยอกเงินและ
> การใช้เอกสารสิทธิปลอมเป็นการกระทำสองกรรมต่างกัน

**ผลเบื้องต้น:** holding ขัดกับ test reference และมีความเสี่ยงอธิบายหลัก
มาตรา 90/91 สลับกัน Keyword checklist แสดง 3/5 แต่เป็น false positive
บางส่วน เพราะพบคำว่า “กรรมเดียว” ในประโยคที่โมเดลใช้ปฏิเสธ holding นั้น

**Artifact:** [TXT เต็ม](results/three-mode-raw-20260730/legal_essay/essay-01-embezzlement-forged-receipt.txt)

</details>

## Legal essay 2 — มัดจำ เบี้ยปรับ และอำนาจศาลลดมัดจำ

<details>
<summary>กดเพื่อดูโจทย์ฉบับเต็ม</summary>

โจทก์และจำเลยทำสัญญาจะซื้อจะขายที่ดินราคา 3,000,000 บาท
โจทก์ชำระเงินจำนวน 300,000 บาทในวันทำสัญญา โดยตกลงว่าเงินดังกล่าว
เป็นหลักฐานการทำสัญญา เป็นประกันการปฏิบัติตามสัญญา และจะนำไปหักออกจาก
ราคาที่ดินเมื่อมีการจดทะเบียนโอนกรรมสิทธิ์ ราคาส่วนที่เหลือกำหนดชำระ
ภายใน 60 วัน

สัญญาระบุว่าหากโจทก์ผิดนัด จำเลยมีสิทธิบอกเลิกสัญญาและริบเงิน
300,000 บาททั้งหมด เมื่อครบกำหนดโจทก์ไม่ชำระราคาส่วนที่เหลือ
จำเลยจึงบอกเลิกสัญญาและริบเงิน ต่อมาจำเลยขายที่ดินให้บุคคลอื่น
ได้ในราคาเดิม และพิสูจน์ความเสียหายได้ 40,000 บาท

โจทก์ฟ้องเรียกเงินคืน 260,000 บาท โดยอ้างว่าแม้เป็นมัดจำ
แต่การริบทั้งหมดสูงเกินส่วนเมื่อเทียบกับความเสียหายจริง

</details>

<details>
<summary>กดเพื่อดู test reference ที่ใช้เปรียบเทียบ</summary>

Test reference จำแนกเงิน 300,000 บาทเป็นมัดจำตาม ป.พ.พ. มาตรา 377
ให้สิทธิริบเมื่อผิดสัญญาตามมาตรา 378 (2) แต่เห็นว่าศาลอาจลดมัดจำ
ที่สูงเกินส่วนตาม พ.ร.บ. ว่าด้วยข้อสัญญาที่ไม่เป็นธรรม พ.ศ. 2540
มาตรา 7

เมื่อพิสูจน์ความเสียหายได้ 40,000 บาท จึงวางผลให้ริบเท่านั้นและคืน
260,000 บาท พร้อมแยกมัดจำจากเบี้ยปรับตามมาตรา 379/383

</details>

<details>
<summary>กดเพื่อดูคำตอบจริงจาก OpenThai</summary>

โมเดลเห็นว่าเงินดังกล่าวเป็นส่วนหนึ่งของราคาที่ดินและคู่สัญญาตกลงให้
ริบได้ทั้งหมด จึงสรุปว่าไม่มีเหตุให้คืน 260,000 บาทและควรยกฟ้อง

โมเดลไม่ได้อ้างมาตรา 377, 378, พ.ร.บ. ว่าด้วยข้อสัญญาที่ไม่เป็นธรรม
มาตรา 7 หรือแยกหลักมาตรา 379/383 ตาม test reference

**ผลเบื้องต้น:** holding ขัด test reference ในสาระสำคัญ
Keyword checklist ผ่าน 1/5 ข้อ แต่ผลนี้ยังไม่ใช่ expert legal score

**Artifact:** [TXT เต็ม](results/three-mode-raw-20260730/legal_essay/essay-02-deposit-penalty-reduction.txt)

</details>

## สรุป Legal essay

| Metric | ผล |
|---|---:|
| จำนวน | 2 |
| ตอบจบโดย `finish_reason=stop` | 2/2 |
| ชน `max_tokens` | 0 |
| เวลาเฉลี่ย | 30.816s |
| Tokens รวม | 2,803 |
| Automated keyword checklist | 40% |
| Holding ตรง test reference จากการอ่านเบื้องต้น | 0/2 |

Keyword checklist ไม่เข้าใจ negation หรือ reasoning จึงไม่ควรใช้เป็น
legal correctness score ควรให้ผู้เชี่ยวชาญตรวจ citation, holding,
coverage และ fluency แยกกันตามแนว model card

# Mode 3 — Closed-book

System prompt:

```python
SYSTEM = (
    "You are an expert on Thai law. You are given ONLY a legal question, "
    "with NO reference material provided. Using your OWN knowledge of Thai "
    "statutes, answer in Thai and cite the specific sections that apply. "
    'Output ONLY JSON: {"answer":"...","citations":[...]}'
)
```

คำถาม 5 ข้อนี้สร้างเพื่อการทดสอบโดย Claude Sonnet 5.0 และไม่มี statute
context ใน prompt Expected sections เป็น test-design assumptions
ไม่ใช่ NitiBench expert ground truth จึงใช้ตรวจเชิงโครงสร้างเบื้องต้นเท่านั้น

## Closed-book 1 — VAT ส่งออกข้าวโพด

<details>
<summary>กดเพื่อดูโจทย์และคำตอบ</summary>

**โจทย์**

บริษัทรับซื้อข้าวโพดจากเกษตรกร นำมาคัดขนาดและอบแห้งโดยยังไม่แปรรูป
แล้วส่งออกทั้งหมด หากขายในประเทศเข้าเกณฑ์ยกเว้นตามมาตรา 81 (1) (ก)
บริษัทจะมีสิทธิเสีย VAT อัตรา 0% ตามมาตรา 80/1 (1) หรือไม่

**คำตอบจริง**

```json
{
  "answer": "บริษัทฯ มีสิทธิเสียภาษีมูลค่าเพิ่มในอัตราร้อยละ 0 ตามมาตรา 80/1 (1) แห่งประมวลรัษฎากร เนื่องจากข้าวโพดที่ขายเป็นพืชผลทางการเกษตรที่ยังมิได้แปรสภาพ และการส่งออกไปจำหน่ายให้แก่ลูกค้าในต่างประเทศถือเป็นการส่งออกสินค้าตามเงื่อนไขที่กฎหมายกำหนดให้ได้รับยกเว้นภาษีมูลค่าเพิ่ม",
  "citations": [
    {"law": "ป.รัษฎากร", "section": "80/1"},
    {"law": "ป.รัษฎากร", "section": "81"}
  ]
}
```

Expected-section check: 2/2 แต่ถ้อยคำ “อัตรา 0%” กับ “ยกเว้น”
ควรให้ผู้เชี่ยวชาญตรวจความแม่นยำ

**Artifact:** [TXT เต็ม](results/three-mode-raw-20260730/closed_book/closed-01-corn-export-vat.txt)

</details>

## Closed-book 2 — บริษัทขายที่ดินหลังถือครอง 6 ปี

<details>
<summary>กดเพื่อดูโจทย์และคำตอบ</summary>

**โจทย์**

บริษัทรับเหมาก่อสร้างซื้อที่ดินเพื่อใช้เป็นสำนักงานและลานเก็บวัสดุ
ต่อมาย้ายสำนักงานและขายที่ดินหลังถือครอง 6 ปี การขายอยู่ในบังคับ
ภาษีธุรกิจเฉพาะตามมาตรา 91/2 (6) หรือไม่

**คำตอบจริง**

```json
{
  "answer": "การขายที่ดินของบริษัทฯ ถือเป็นการขายอสังหาริมทรัพย์เป็นทางค้าหรือหากำไรอันต้องเสียภาษีธุรกิจเฉพาะตามมาตรา 91/2 (6) แห่งประมวลรัษฎากร ...",
  "citations": [
    {"law": "ป.รัษฎากร", "section": "91/2"}
  ]
}
```

Expected-section check: 1/1 ส่วนเงื่อนไขและกฎหมายลำดับรองยังต้องตรวจ
โดยผู้เชี่ยวชาญ

**Artifact:** [TXT เต็ม](results/three-mode-raw-20260730/closed_book/closed-02-company-land-sbt.txt)

</details>

## Closed-book 3 — จำหน่ายหนี้สูญ

<details>
<summary>กดเพื่อดูโจทย์และคำตอบ</summary>

**โจทย์**

บริษัทมีลูกหนี้การค้า 800,000 บาท ติดตามทวงถามแล้ว ลูกหนี้เลิกกิจการ
และไม่มีทรัพย์สินให้บังคับ บริษัทต้องการจำหน่ายหนี้สูญเป็นรายจ่าย
ต้องใช้มาตราใดและกฎหมายลำดับรองฉบับใด

**คำตอบจริง**

```json
{
  "answer": "การจำหน่ายหนี้สูญของบริษัทฯ ในกรณีนี้อยู่ภายใต้บังคับมาตรา 65/9 แห่งประมวลรัษฎากร โดยต้องเป็นไปตาม ... กฎกระทรวงฉบับที่ 118 (พ.ศ. 2534)",
  "citations": [
    {"law": "ป.รัษฎากร", "section": "65/9"}
  ]
}
```

Test design คาด `มาตรา 65 ทวิ (9)` และกฎกระทรวง ฉบับที่ 186
จึงไม่ตรง expected-section check

**Artifact:** [TXT เต็ม](results/three-mode-raw-20260730/closed_book/closed-03-bad-debt-writeoff.txt)

</details>

## Closed-book 4 — ค่าบริการแก่บริษัทสิงคโปร์

<details>
<summary>กดเพื่อดูโจทย์และคำตอบ</summary>

**โจทย์**

บริษัทไทยจ่ายค่าที่ปรึกษาการตลาดให้บริษัทสิงคโปร์ซึ่งไม่มีสถานประกอบการถาวร
ในไทยและทำงานทั้งหมดจากสิงคโปร์ บริษัทไทยต้องหักภาษีตามมาตราใด

**คำตอบจริง**

```json
{
  "answer": "บริษัทฯ มีหน้าที่ต้องหักภาษี ณ ที่จ่ายและนำส่งตามมาตรา 50 แห่งประมวลรัษฎากร ...",
  "citations": [
    {"law": "ป.รัษฎากร", "section": "50"}
  ]
}
```

Test design คาดให้วิเคราะห์มาตรา 70 ประกอบอนุสัญญาภาษีซ้อนไทย–สิงคโปร์
จึงไม่ตรง expected-section check

**Artifact:** [TXT เต็ม](results/three-mode-raw-20260730/closed_book/closed-04-singapore-service-withholding.txt)

</details>

## Closed-book 5 — บ้านพักที่นายจ้างจัดให้

<details>
<summary>กดเพื่อดูโจทย์และคำตอบ</summary>

**โจทย์**

บริษัทเช่าบ้านจากบุคคลภายนอกและให้ผู้บริหารพักโดยไม่คิดค่าเช่า
มูลค่าการอยู่อาศัยเป็นเงินได้พึงประเมินตามมาตราใด และต้องรวมคำนวณ
ภาษีเงินได้บุคคลธรรมดาหรือไม่

**คำตอบจริง**

```json
{
  "answer": "มูลค่าของการได้อยู่อาศัยในบ้านพักโดยไม่เสียค่าเช่า ถือเป็นเงินได้พึงประเมินตามมาตรา 40 แห่งประมวลรัษฎากร พนักงานมีหน้าที่ต้องนำมูลค่าดังกล่าวไปรวมคำนวณเพื่อเสียภาษีเงินได้บุคคลธรรมดา",
  "citations": [
    {"law": "ประมวลรัษฎากร", "section": "40"}
  ]
}
```

Test design คาดมาตรา 39 และ 40 (1) โมเดลจึงตรงบางส่วน

**Artifact:** [TXT เต็ม](results/three-mode-raw-20260730/closed_book/closed-05-employee-housing-benefit.txt)

</details>

## สรุป Closed-book

| Metric | ผล |
|---|---:|
| จำนวน | 5 |
| Valid JSON | 5/5 |
| Expected-section macro recall | 50% |
| เวลาเฉลี่ย | 5.881s |
| Tokens รวม | 3,035 |
| ชน `max_tokens` | 0 |

Closed-book ตอบเร็วและรักษา JSON contract ได้ดี แต่เลขมาตราและกฎหมายลำดับรอง
ยังไม่สม่ำเสมอ จึงเหมาะกับการหา issue/keyword เบื้องต้นมากกว่าการยืนยัน
ข้อกฎหมายโดยไม่มีแหล่งอ้างอิง

# ข้อสรุปเชิงระบบ

1. **Citation RAG เป็นเส้นทางที่แข็งแรงที่สุดในชุดนี้**
   เมื่อ retriever ส่งมาตราที่ถูก OpenThai ตอบและอ้างมาตราตรง NitiBench
   ครบ 5/5 ทั้ง PostgreSQL และ Milvus

2. **คุณภาพ retrieval สำคัญกว่า vector database เพียงอย่างเดียว**
   ทั้งสอง backend ให้คำตอบเท่ากัน ความต่างหลักใน sample นี้คือ latency
   ไม่ใช่ citation quality

3. **Milvus ลด retrieval latency แต่ LLM ยังเป็นคอขวด**
   Milvus retrieval รวม embedding เฉลี่ย 0.057s แต่ end-to-end 7.280s
   เวลาส่วนใหญ่จึงอยู่ที่ OpenThai rerank และ generation

4. **PostgreSQL ยังเป็น baseline ที่ใช้งานได้ดี**
   เหมาะเมื่อมี PostgreSQL อยู่แล้ว ต้องการ transactional metadata,
   SQL filtering และขนาด/traffic ยังไม่สูง

5. **หนึ่งมาตราต่อหนึ่ง chunk ช่วย citation contract**
   `law_name` + `section_num` + body ที่ตัด repeated heading ออก
   ทำให้ embedding ไม่ซ้ำ metadata และประกอบ `<law>` context ได้ตรง
   รูปแบบที่โมเดลถูกฝึก

6. **Reranker ต้องมี structured-output guard**
   พบ JSON ขาดวงเล็บหนึ่งครั้ง แม้ model intent เลือก candidate ถูก
   จึงต้อง validate/recover syntax โดยไม่ hardcode มาตรา

7. **Legal essay ต้องใช้ semantic/expert judge**
   Keyword checklist ให้คะแนนเกินจริงเมื่อคำสำคัญอยู่ในประโยคปฏิเสธ
   ควรตรวจ citation, holding, coverage และ fluency แยกกัน

8. **Closed-book ไม่ควรใช้ยืนยันเลขมาตราในงาน high-stakes**
   รอบนี้ valid JSON ครบ แต่ expected-section macro recall เพียง 50%
   และพลาดกฎหมายลำดับรอง/อนุสัญญาในคำถามภาษีที่ซับซ้อน

# ขอบเขตและข้อจำกัด

- RAG มีเพียง 5 คำถาม และแต่ละข้อมี positive section หลักหนึ่งมาตรา
- ชุด 5 ข้อเป็น fixed test set ใน runner ไม่ใช่ auditable random sample
- PostgreSQL และ Milvus ใช้ sparse retrieval/RRF configuration ต่างกัน
- การวัดเวลาเกิดคนละรอบ จึงได้รับผลจาก warm-up, cache และภาระของเครื่อง
- ไม่ใช่ stress, concurrency หรือ production load benchmark
- Token ที่ต่างกันเกิดจาก candidate packet ต่างกัน ไม่ได้แปลว่าเปลี่ยน
  database แล้ว token จะลดลงเสมอ
- RAG citation ตรง ground truth ไม่รับรองว่าคำตอบครอบคลุมข้อเท็จจริงจริง
  ข้อยกเว้น กฎหมายลำดับรอง หรือกฎหมายที่แก้ไขภายหลัง
- Legal essay references สร้างเพื่อการทดสอบโดย ChatGPT 5.6 sol
  และ Closed-book test design สร้างโดย Claude Sonnet 5.0
  ทั้งสองส่วนยังไม่ได้ผ่าน legal-expert adjudication
- Automated checklist และ expected-section matching ไม่ใช่คำวินิจฉัยกฎหมาย
- ก่อนใช้จริงต้องตรวจตัวบทฉบับปัจจุบัน แหล่งทางการ และให้ผู้เชี่ยวชาญ
  ตรวจคำตอบ โดยเฉพาะงานภาษี คดีอาญา และข้อพิพาท

Repository นี้ไม่เก็บ model weights, database credentials, access token
หรือ chat sessions
