# OpenThai 2.0 Legal: Thai Legal RAG benchmark

การทดสอบแบบตรวจย้อนกลับได้ของ
[OpenThai 2.0 Legal](https://huggingface.co/iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b)
กับ RAG เอกสารภาษาไทย เปรียบเทียบผลที่บันทึกไว้ของ 3 runtime

| Model / runtime | รูปแบบรัน |
|---|---|
| OpenThai 2.0 Legal · Ollama Q4 | quantized Q4 ผ่าน Ollama |
| OpenThai 2.0 Legal · vLLM BF16 | local safetensors BF16 ผ่าน vLLM 0.25.1 |
| Qwen3.6-35B-A3B · llama.cpp Q5 | quantized Q5 ผ่าน llama.cpp |

> ผลทั้งหมดเป็น **preliminary / unreviewed** ไม่ใช่คำแนะนำหรือคำวินิจฉัยทางกฎหมาย
> การนำไปใช้จริงต้องให้ผู้เชี่ยวชาญกฎหมายไทยตรวจตัวบทฉบับปัจจุบัน ข้อเท็จจริง และข้อยกเว้น

## ชุดข้อมูล

| Dataset | แหล่งข้อมูล | Retrieval corpus | Provenance |
|---|---|---:|---|
| NitiBench | [VISAI-AI/NitiBench](https://huggingface.co/datasets/VISAI-AI/nitibench) | 3,934 legal chunks | passage embedding ใช้เฉพาะตัวบท ไม่ใส่คำตอบหรือเฉลย |
| พ.ร.บ. การประกอบธุรกิจข้อมูลเครดิต (NCB) | [BOT principal text Updated-2559](https://www.bot.or.th/content/dam/bot/documents/th/laws-and-rules/laws-and-regulations/legal-department/7-ncb-act/7-1-ncb-act/7.1.2-Law_TH_CreditBureau%20Updated-2559.pdf) | 225 units (73 parent + 152 child) | corpus ฉบับรวม 1–6; แยกมาตรา/ข้อย่อย พร้อม page index |
| BOT Digital Fraud Management | [BOT 2568/0254](https://www.bot.or.th/content/dam/bot/fipcs/documents/FPG/2568/ThaiPDF/25680254.pdf) | 54 units | แยกตามข้อ/ข้อย่อย พร้อมเลขหน้า |

NCB และ Digital Fraud เป็นการ extract ตัวบทให้แยกข้อกำหนดและ citation ได้ ไม่ใช่ scenario Q&A
จากเหตุการณ์จริง จึงควรวัดต่อกับโจทย์ข้อเท็จจริงที่หลากหลายก่อนใช้งานจริง

## วิธีทดสอบและ leakage controls

ใช้คำถามคงที่ 15 ข้อ (3 datasets × 5) โดย Q4 และ Qwen รับ final evidence ที่ retrieve/rerank
มาแล้วชุดเดียวกัน ส่วน BF16 reconstruct final evidence ชุดเดียวกันจากไฟล์ frozen ที่ไม่มี label
และ **ไม่ได้ rerun retriever** เพราะ VRAM ถูกใช้กับ BF16 model อยู่

```text
Question
  ├─ Dense: Qwen3-Embedding-4B, 2,560 dims, L2
  ├─ Sparse: lexical / Thai n-gram
  └─ Hybrid fusion + rerank
          ↓
    top_k = 8 final evidence packet
          ↓
    OpenThai Q4 · OpenThai BF16 · Qwen Q5
          ↓
   JSON answer + citation → score หลัง inference เท่านั้น
```

| Parameter | ค่า |
|---|---:|
| retrieval top_k | 8 |
| dense embedding | Qwen3-Embedding-4B, 2,560 dimensions, L2-normalized |
| generation temperature / top_p | 0.0 / 1.0 |
| generation max_tokens | 2,048 |
| seed | 42 |
| output contract | JSON answer + grounded citations |
| BF16 vLLM | vLLM 0.25.1, max model len 32,768, eager + Triton MoE |

`expected citation`, `reference answer` และเฉลยไม่เข้าสู่ embedding, retriever, reranker,
frozen evidence input หรือ generation prompt ใช้หลัง inference เพื่อวัด metric เท่านั้น

## ตัวอย่าง UI: คำถาม + evidence เดียวกัน + คำตอบ 3 โมเดล

หน้า `ผลทดสอบ` ของ Legal RAG Lab แสดง evidence ที่ส่งให้โมเดลเพียงครั้งเดียวเหนือ answer cards
จึงเปรียบเทียบคำตอบและ citation ของทั้งสามโมเดลได้โดยไม่ต้องใช้ภาพจำนวนมาก

### NitiBench

<img src="assets/ui-three-model-comparison-20260812/01-nitibench-three-model-comparison.png" alt="NitiBench: evidence and three model answers" width="1600">

### พ.ร.บ. การประกอบธุรกิจข้อมูลเครดิต (NCB)

<img src="assets/ui-three-model-comparison-20260812/02-ncb-three-model-comparison.png" alt="NCB: evidence and three model answers" width="1600">

### BOT Digital Fraud Management

<img src="assets/ui-three-model-comparison-20260812/03-digital-fraud-three-model-comparison.png" alt="Digital Fraud: evidence and three model answers" width="1600">

## ผลเชิงเทคนิคหลัง inference

`Expected-citation recall` และ `citation precision` ด้านล่างคำนวณหลังโมเดลตอบแล้ว
จึงไม่ใช่สัญญาณว่ามีเฉลยอยู่ใน RAG context; metric เหล่านี้ไม่ตัดสินความถูกต้องทางกฎหมาย

### 1) NitiBench — 5 ข้อ

| Metric | OpenThai Q4 | OpenThai BF16 | Qwen Q5 |
|---|---:|---:|---:|
| candidate recall@8 | 100% | 100% (frozen packet) | 100% (shared packet) |
| expected-citation recall | 100% | 100% | 100% |
| citation precision | 100% | 100% | 100% |
| JSON valid | 5/5 | 5/5 | 5/5 |
| grounded citations | 5/5 | 5/5 | 5/5 |

### 2) พ.ร.บ. การประกอบธุรกิจข้อมูลเครดิต (NCB) — 5 ข้อ

| Metric | OpenThai Q4 | OpenThai BF16 | Qwen Q5 |
|---|---:|---:|---:|
| candidate recall@8 | 100% | 100% (frozen packet) | 100% (shared packet) |
| expected-citation recall | 100% | 100% | 100% |
| citation precision | 100% | 90% | 100% |
| JSON valid | 5/5 | 5/5 | 5/5 |
| grounded citations | 5/5 | 5/5 | 5/5 |

### 3) BOT Digital Fraud Management — 5 ข้อ

| Metric | OpenThai Q4 | OpenThai BF16 | Qwen Q5 |
|---|---:|---:|---:|
| candidate recall@8 | 100% | 100% (frozen packet) | 100% (shared packet) |
| expected-citation recall | 70% | 80% | 100% |
| citation precision | 100% | 83.33% | 100% |
| JSON valid | 5/5 | 5/5 | 5/5 |
| grounded citations | 5/5 | 5/5 | 5/5 |

ผล BF16 รอบนี้ใช้ evidence เดิม จึงบอกได้เฉพาะความต่างของการเรียบเรียงคำตอบ/citation
หลังรับ context เดียวกัน—not a fresh end-to-end retrieval or latency comparison

## คุณภาพการเรียบเรียงภาษาไทย — Codex Sol blind review

Codex Sol ประเมินคำตอบ 45 ชิ้นแบบ blind: ต่อหนึ่งข้อสลับคำตอบเป็น A/B/C แบบ deterministic
และปิดชื่อโมเดล, evidence, citation, expected/reference answer, score เดิม, เวลา และ token ก่อนตรึงคะแนน
เกณฑ์มี 4 ด้าน ด้านละ 0–5: ความลื่นไหลภาษาไทย, ความชัดของ actor/condition/exception
ตามที่สื่อ, การจัดลำดับ/ความตรงประเด็น และความครอบคลุมที่สื่อออกมา

| Model / runtime | เฉลี่ย /20 | Median | รวม /300 | ชนะเดี่ยว | มีส่วนในผลเสมอ |
|---|---:|---:|---:|---:|---:|
| OpenThai 2.0 Legal · Ollama Q4 | 15.87 | 16 | 238 | 0 | 4 |
| OpenThai 2.0 Legal · vLLM BF16 | 19.13 | 19 | 287 | 2 | 8 |
| Qwen3.6-35B-A3B · llama.cpp Q5 | 19.47 | 20 | 292 | 4 | 9 |

| Dataset | OpenThai Q4 | OpenThai BF16 | Qwen Q5 |
|---|---:|---:|---:|
| NitiBench | 17.00 | 19.20 | 19.60 |
| NCB | 16.60 | 19.40 | 19.80 |
| Digital Fraud | 14.00 | 18.80 | 19.00 |

| มิติ /5 | OpenThai Q4 | OpenThai BF16 | Qwen Q5 |
|---|---:|---:|---:|
| ความลื่นไหลและอ่านง่าย | 3.33 | 4.87 | 4.93 |
| ความชัด actor / condition / exception ตามที่เขียน | 3.80 | 4.80 | 5.00 |
| การจัดลำดับและความตรงประเด็น | 4.33 | 4.73 | 4.53 |
| ความครอบคลุมที่สื่อออกมา | 4.40 | 4.73 | 5.00 |

ภายใน 15 คำตอบที่บันทึกไว้ BF16 เพิ่มจาก Q4 เฉลี่ย **3.27/20** และคะแนนรวมต่าง Qwen
เพียง **5/300**; BF16 สูงกว่า Q4 10 ข้อ, เท่ากัน 4 ข้อ และต่ำกว่า 1 ข้อ
ส่วน Qwen สูงกว่า BF16 5 ข้อ, BF16 สูงกว่า Qwen 2 ข้อ และเสมอ 8 ข้อ

ผลนี้วัด **เฉพาะภาษาและการสื่อสาร** ไม่วัด retrieval, grounding, citation correctness,
ความเร็ว หรือความถูกต้องทางกฎหมาย และ Codex Sol ไม่ใช่ผู้เชี่ยวชาญกฎหมายไทย
การตัดสินสาระสำคัญควรใช้ Thai legal-expert adjudication แบบปิดชื่อโมเดลร่วมกับตัวบทจริง

## ไฟล์ผลลัพธ์ครบทุกข้อ ทุกโมเดล ทุก dataset

ผลที่เผยแพร่ถูกย่อให้มีเฉพาะคำถาม, evidence ที่คัดเลือก, คำตอบ, citation, เวลา, metric หลัง inference
และคะแนน blind language review ไม่มี raw prompt, reference answer หรือ expected-citation label

- [Manifest และขอบเขตไฟล์](results/three-model-benchmark-20260812/manifest.json)
- [ผลรวม 15 ข้อ / 3 โมเดล](results/three-model-benchmark-20260812/all_cases.json)
- [ผลรายข้อแยก 15 ไฟล์](results/three-model-benchmark-20260812/cases/)
- [Codex Sol blind language review (Markdown)](results/three-model-benchmark-20260812/language_blind_review.md)
- [Codex Sol blind language review (JSON)](results/three-model-benchmark-20260812/language_blind_review.json)

SHA-256 ของ source artifacts, จำนวน case และรายการไฟล์อยู่ใน manifest เพื่อให้ตรวจการแปลงผลได้

## ข้อจำกัด

- เป็น fixed benchmark 15 ข้อ ไม่ใช่ตัวอย่างสุ่มหรือการวัด coverage ของกฎหมายไทยทั้งหมด
- BF16 ใช้ frozen final evidence ชุดเดียวกับ Q4/Qwen; ยังไม่มีผลรอบ fresh retrieval ของ BF16
- เวลาแต่ละ run อยู่คนละ runtime/cache จึงไม่ควรใช้ตัดสิน production latency หรือ concurrency
- Citation metric ตรวจความสอดคล้องกับ label หลัง inference ไม่แทนการอ่านตัวบทหรือการตีความทางกฎหมาย
- ต้องเพิ่มโจทย์หลายมาตรา ข้อยกเว้น กฎหมายชื่อใกล้กัน และข้อเท็จจริงจริง พร้อม human review ก่อนใช้งาน
- repository นี้ไม่เก็บ model weights, credential, token หรือ chat session
