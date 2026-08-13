# OpenThai 2.0 Legal: Thai Legal RAG benchmark

การทดสอบแบบตรวจย้อนกลับได้ของ
[OpenThai 2.0 Legal](https://huggingface.co/iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b)
กับ RAG เอกสารภาษาไทย เปรียบเทียบผลที่บันทึกไว้ของ 2 runtime ในรอบล่าสุด

| Model / runtime | รูปแบบรัน |
|---|---|
| OpenThai 2.0 Legal · vLLM BF16 | local safetensors BF16 ผ่าน vLLM 0.25.1 |
| Qwen3.6-35B-A3B · llama.cpp Q5 | quantized Q5 ผ่าน llama.cpp |

> ผลทั้งหมดเป็น **preliminary / unreviewed** ไม่ใช่คำแนะนำหรือคำวินิจฉัยทางกฎหมาย
> การนำไปใช้จริงต้องให้ผู้เชี่ยวชาญกฎหมายไทยตรวจตัวบทฉบับปัจจุบัน ข้อเท็จจริง และข้อยกเว้น

## Latest: wide-context comparison — 13 August 2026

รอบล่าสุดเปรียบเทียบเฉพาะ **OpenThai 2.0 Legal vLLM BF16** และ
**Qwen3.6-35B-A3B llama.cpp Q5** บนคำถามคงที่ 15 ข้อ (NitiBench, NCB และ
Digital Fraud อย่างละ 5 ข้อ) ด้วย input ชุดเดียวกันอย่างตรวจย้อนกลับได้

- OpenThai Ollama Q4 ถูกถอดออกจาก Ollama ตามคำสั่งผู้ใช้ และ **ไม่ถูกนำมาเทียบในตารางนี้**
  รวมทั้งไม่ใช้ผลเก่ามาปะปนกับรอบใหม่
- ทุกคำถามได้รับ system prompt เดียวกัน (SHA-256
  `32b66676fcb8f90dccc28152cc1424dcdbed32c0949e33751720c5fd277097a0`), evidence 8
  แถวชุดเดียวกัน, `temperature=0`, `top_p=1`, `max_tokens=2048`, `seed=42`,
  และปิด thinking
- input ไม่มี answer, reference answer, expected law หรือ expected section; labels ใช้ใน
  scorer **หลัง** generation เท่านั้น

| Dataset / 5 cases | Runtime | JSON valid | all citations grounded | expected-citation recall | citation precision | mean answer time |
|---|---|---:|---:|---:|---:|---:|
| NitiBench | OpenThai BF16 / vLLM | 5/5 | 5/5 | 1.00 | 1.00 | 0.8820 s |
| NitiBench | Qwen3.6 Q5 / llama.cpp | 5/5 | 5/5 | 1.00 | 1.00 | 1.3370 s |
| NCB | OpenThai BF16 / vLLM | 5/5 | 5/5 | 0.80 | 1.00 | 1.3014 s |
| NCB | Qwen3.6 Q5 / llama.cpp | 5/5 | 5/5 | 1.00 | 1.00 | 2.7195 s |
| Digital Fraud | OpenThai BF16 / vLLM | 5/5 | 4/5 | 0.40 | 0.80 | 2.5440 s |
| Digital Fraud | Qwen3.6 Q5 / llama.cpp | 5/5 | 3/5 | 0.40 | 0.60 | 3.1433 s |

`expected-citation recall` และ `citation precision` เป็น diagnostic หลัง inference ไม่ใช่
คำรับรองว่าคำตอบครบหรือเป็นบทที่ควบคุมกรณีเสมอไป. เวลาเป็น sequential observation บน host
เดียว ไม่ใช่ production latency claim.

### ข้อค้นพบเชิงเนื้อหาโดย GPT-5.6 Sol

| ประเด็น | OpenThai BF16 | Qwen Q5 |
|---|---|---|
| NitiBench | ผ่านสาระ/มาตรา 5/5 | ผ่านสาระ/มาตรา 5/5 |
| NCB | 3 pass, 1 partial, 1 needs correction | 5 pass |
| Digital Fraud | 2 pass, 2 partial, 1 evidence-limited | 2 pass, 2 partial, 1 evidence-limited |

- BF16 เด่นเรื่องความเร็วและ NitiBench ที่ตรงครบ แต่ใน NCB มีคำตอบ “ภายใน 30 วัน”
  ที่ตัดผู้มีหน้าที่/การกระทำออก และในเคสการเปิดเผยโดยมิชอบตอบเฉพาะค่าสินไหมตามมาตรา 41
  โดยไม่ได้กล่าวถึงมาตรา 51 ซึ่งเป็น expected scorer label ของโจทย์หลัง inference
- Qwen ครอบคลุม actor/action/condition ของ NCB ได้ครบกว่าในรอบนี้ แต่ใน Digital Fraud ยังเขียน
  citation ระดับต้องห้าม เช่น `5.3.2 (2)` และ `5.3.5`; corpus อนุญาตให้อ้างได้เฉพาะ X.X จึงต้อง
  normalize/validate เป็น owner `5.3` ก่อนส่งคำตอบ
- คำถาม scope ของ Digital Fraud เป็น **evidence-limited** ทั้งคู่: lexical top-8 ไม่พา 4.1–4.3
  เข้ามาเลย จึงไม่ควรใช้ผล 0.40 เพื่อสรุปความสามารถ reasoning ของโมเดลหรือคุณภาพ hybrid retrieval

<details>
<summary>เปิดดู 2 เคส NCB ที่ต่างกัน: ใช้ context เดียวกันจริงหรือไม่</summary>

ทั้ง BF16 และ Qwen ได้ prompt และ top-8 evidence **ชุดเดียวกัน** ในแต่ละแถวด้านล่าง; Qwen
ไม่ได้ retrieve หรือรับ context เพิ่ม. ความต่างจึงเป็นการเลือกและสังเคราะห์สาระจาก candidate
ที่มีอยู่แล้ว.

| Case | Relevant sections already in the shared top-8 | OpenThai BF16 | Qwen Q5 | Reading |
|---|---|---|---|---|
| ขอแก้ไข/ตรวจสอบข้อมูลเครดิต | `26, 19, 25, 17, 48, 20, 3, 27` | “ภายในสามสิบวันนับแต่วันที่ได้รับคำขอ” — cite 26 | “บริษัทข้อมูลเครดิตหรือสมาชิกต้องแจ้งผลการตรวจสอบหรือแก้ไขข้อมูลพร้อมเหตุผลให้เจ้าของข้อมูลทราบภายในสามสิบวันนับแต่วันที่ได้รับคำขอ” — cite 26 | ทั้งคู่เห็น ม.26 เท่านั้นเป็นหลัก; Qwen เก็บ actor, action, reason และเวลาไว้ครบกว่า ไม่ใช่ evidence เพิ่ม |
| เปิดเผยข้อมูลนอกวัตถุประสงค์มีโทษ | `41, 17, 3, 51, 61, 20, 24, 22` | สรุปค่าสินไหมทดแทน — cite 41 | แยกค่าสินไหมตาม 41 และโทษจำคุกไม่เกิน 3 ปี/ปรับไม่เกิน 300,000 บาท/ทั้งจำทั้งปรับตาม 51 — cite 41, 51 | scorer กำหนด expected section=51 หลัง inference. Codex Sol อ่านแยกแล้วเห็นว่า ม.51 เป็นสาระสำคัญต่อการตอบคำว่า “โทษ” โดยตรง ขณะที่ ม.41 กล่าวถึงค่าสินไหม; Qwen ตอบกว้างกว่าแต่ grounded. นี่ไม่ใช่ legal-expert adjudication |

</details>

### UI comparison: Qwen Q5 vs OpenThai BF16 ครบ 15 ข้อ

หน้า `ผลเปรียบเทียบ RAG แบบควบคุม` แสดงคำถามละ 4 คอลัมน์: คำตอบ Qwen Q5, คำตอบ
OpenThai BF16, ผลต่าง retrieval และผลต่างคำตอบที่ GPT-5.6 Sol review. ก่อน render ทุกแถว
ตรวจว่า ordered top-8, จำนวน context characters และสถานะ truncation ตรงกันทั้งสอง runtime;
จึงไม่สรุปความต่างของคำตอบว่าเกิดจาก model จนกว่าจะผ่าน gate นี้. คำตอบเต็ม, citation และ
top-8 แต่ละข้อเปิดดูได้จาก card ใน UI.

ใน NCB penalty card ที่ขีดกรอบทอง ระบบแยกให้ชัดว่า `51` เป็น expected scorer label หลัง
inference ไม่ได้ส่งเข้า prompt/retrieval และวางประเด็นชวนทบทวนไว้ว่า คำว่า “มีโทษอย่างไร”
ครอบคลุมมาตรา 51 หรือไม่. GPT-5.6 Sol เห็นว่าเป็นประเด็นสำคัญต่อการตอบเรื่องโทษโดยตรง
แต่การเข้าข่ายจริงยังต้องเทียบข้อเท็จจริงกับองค์ประกอบของมาตรา 41 และ 51 โดยผู้เชี่ยวชาญกฎหมาย.

#### NitiBench — 5 ข้อ

<img src="assets/ui-controlled-comparison-20260813/01-nitibench-qwen-vs-bf16.png" alt="Controlled UI comparison of all five NitiBench cases: Qwen Q5, OpenThai BF16, retrieval differences, and GPT-5.6 Sol review" width="1600">

#### NCB — 5 ข้อ

<img src="assets/ui-controlled-comparison-20260813/02-ncb-qwen-vs-bf16.png" alt="Controlled UI comparison of all five NCB cases including the highlighted sections 41 and 51 penalty question" width="1600">

#### BOT Digital Fraud — 5 ข้อ

<img src="assets/ui-controlled-comparison-20260813/03-digital-fraud-qwen-vs-bf16.png" alt="Controlled UI comparison of all five Digital Fraud cases including retrieval limitations and citation-level review" width="1600">

### โครงสร้างข้อมูลและ context ที่ทดสอบ

| Dataset | Retrieval child | Parent | สถานะที่ยืนยัน |
|---|---|---:|---|
| NCB | มาตรา | 9 หมวด | 66 มาตรา จาก PDF BOT หน้า 1–18; เอา footer ออกและไม่มีมาตราซ้ำ |
| Digital Fraud | ข้อ X.X | 6 ข้อหลัก | 11 children จาก PDF BOT หน้า 2–13; X.X.X รวมในเนื้อหา X.X เจ้าของและห้ามเป็น citation/retrieval row แยก |

NitiBench ใช้ frozen label-free hybrid packet ที่มีอยู่แล้ว. ส่วน NCB และ Digital Fraud ในรอบนี้ใช้
Thai lexical + character 3/4-gram fallback เพราะ embedding service ไม่พร้อมระหว่าง BF16 ใช้ GPU;
จึงเป็นการวัด **wide-context answer synthesis** ไม่ใช่ตัวเลขประสิทธิภาพ hybrid retrieval ใหม่.
ทุกเคสไม่มี context truncation และ grouped child `5.3` ส่งเนื้อหา `5.3.1`–`5.3.6` ครบถึงโมเดล.

### ภาพ capture ที่ตรวจแล้ว

ภาพตารางด้านล่างถูกถ่ายหลัง script รอให้มีแถวข้อมูลจริง ไม่ใช่ระหว่างสถานะ loading.

<img src="assets/ui-dataset-structure-20260813/ncb-66-article-table.png" alt="NCB dataset table showing 66 article children and parent provenance" width="1200">

<img src="assets/ui-dataset-structure-20260813/digital-fraud-11-x-x-table.png" alt="Digital Fraud dataset table showing 11 X.X children and parent provenance" width="1200">

### แนวทางปรับใช้และข้อควรระวัง

1. จำกัด citation ของ Digital Fraud เป็น X.X แล้ว reject X.X.X แม้ข้อความในคำตอบจะถูกต้อง
2. ทำ candidate-admission gate: คำถาม scope ต้องมี scope provision ใน evidence ก่อนตอบแบบ definitive;
   หากไม่มีให้ retrieve ใหม่หรือแจ้ง evidence insufficient
3. ก่อน final answer ใช้ checklist แบบ label-free ให้คง duty bearer/right holder, action/right,
   condition/exception, และ deadline/written notice เพื่อกันคำตอบสั้นเกิน เช่น “30 วัน”
4. ใช้ top-1 NCB เฉพาะเมื่อ confidence margin สูงและพิสูจน์ได้ว่าเป็นคำถามมาตราเดียว; ห้ามเปิดใช้
   เป็น global default เพราะจะเสีย multi-provision context

รายละเอียดการอ่านคำตอบรายประเด็นและ artifact contract อยู่ที่
[Codex Sol wide-context evaluation](reports/wide-context-qwen-q5-vs-openthai-bf16-20260813.md);
สรุปใน README นี้ไม่ใช่ legal certification.

## Earlier parent-explicit three-runtime test — 13 August 2026

ส่วนนี้เก็บไว้เป็นประวัติของ run ก่อนหน้าเท่านั้น ซึ่งยังมี OpenThai Q4 อยู่ในตารางเดิม;
ไม่ใช่ผลเปรียบเทียบที่ใช้สรุปรอบล่าสุดด้านบน.

รอบล่าสุดทดสอบคำถามคงที่ 10 ข้อ โดยใช้ dataset ทางการที่จัดโครงสร้างใหม่: NCB 5 ข้อ และ
BOT Digital Fraud 5 ข้อ. ทุกคำถามใช้ final evidence packet เดียวกันจาก run Qwen/Q4 เดิม
(4 children ต่อคำถาม) แล้ว replay request เดิมให้ OpenThai BF16 บน vLLM เพื่อแยกผลของ
การสร้างคำตอบออกจากผล retrieval. Expected sections ใช้ **หลัง inference เท่านั้น**.

| Dataset / 5 cases | Model/runtime | JSON valid | all citations grounded | expected-citation recall | citation precision | mean answer time |
|---|---|---:|---:|---:|---:|---:|
| NCB | OpenThai Q4 / Ollama | 5/5 | 5/5 | 1.00 | 1.00 | 3.3457 s |
| NCB | OpenThai BF16 / vLLM | 5/5 | 5/5 | 1.00 | 1.00 | 0.9189 s |
| NCB | Qwen3.6-35B-A3B Q5 / llama-server 8081 | 5/5 | 5/5 | 1.00 | 1.00 | 2.4168 s |
| Digital Fraud | OpenThai Q4 / Ollama | 3/5 | 3/5 | 0.40 | 0.60 | 3.9413 s |
| Digital Fraud | OpenThai BF16 / vLLM | 5/5 | 5/5 | 0.80 | 1.00 | 2.1100 s |
| Digital Fraud | Qwen3.6-35B-A3B Q5 / llama-server 8081 | 5/5 | 5/5 | 0.80 | 1.00 | 2.4952 s |

OpenThai BF16 was served by vLLM 0.25.1 with `dtype=bfloat16`, `max_model_len=32768`,
Triton MoE, temperature 0.0, top_p 1.0, max_tokens 2,048, and seed 42. The runtime used
the native sampler (`VLLM_USE_FLASHINFER_SAMPLER=0`) to avoid an environment-specific
FlashInfer JIT path issue; this is a serving-backend setting, not a change to model weights.

### Evidence-grounded answer review

Codex Sol reviewed the generated answers against the **rendered evidence actually sent to the
model**, not citation metrics alone. The baseline BF16 review found 5 pass, 3 partial, 0 needs
correction, and 2 evidence-limited answers. Qwen/Q4 counts below are the original review of
the same frozen packets; all three results remain preliminary and require legal-expert
adjudication.

| Model/runtime | pass | partial | needs correction | evidence-limited |
|---|---:|---:|---:|---:|
| OpenThai Q4 / Ollama | 4 | 1 | 4 | 1 |
| OpenThai BF16 / vLLM | 5 | 3 | 0 | 2 |
| Qwen3.6-35B-A3B Q5 / llama-server 8081 | 7 | 1 | 1 | 1 |

The test verifies direct parent provenance for all 40 selected rows: every child carries
`parent_id`, `parent_section`, `parent_heading`, and `parent_relation=child_of`; all ten
rendered prompts expose parent section and heading.

### Follow-up: full grouped-child renderer validation

The Digital Fraud prompt renderer has now been repaired and revalidated with OpenThai BF16.
It uses a 30,000-character total budget, an 18,000-character per-evidence allowance, and a
1,200-character reservation for every remaining evidence row. For all four frozen packets
that select child `5.3`, its complete 16,830-character body—including source headings
`5.3.1`–`5.3.6`—reached the model without truncation. It remains one retrievable/citable
`5.3` block; no `X.X.X` evidence row or citation target was created.

This follow-up is a **generation-only renderer validation**, not a fresh retrieval benchmark:
it reuses the five question/evidence selections from the baseline, restores raw content from
the active corpus by ID, and changes the renderer and citation instruction. It therefore does
not replace the comparison table above or claim a latency comparison.

| BOT validation / 5 cases | Result |
|---|---:|
| full `5.3` packets with no truncation | 4/4 |
| valid JSON | 5/5 |
| cited ID occurs in selected evidence | 5/5 |
| expected-section recall (post-inference diagnostic) | 0.40 |
| mean answer time | 2.506 s |
| Codex Sol review: pass / partial / needs correction / evidence-limited | 1 / 1 / 2 / 1 |

`cited ID occurs in selected evidence` is identifier-level grounding only. In the full-text
validation, monitoring accurately used `5.3` content but cited `5.4`; reporting accurately
used nested source item `5.3.5` but cited `5.2`. These are model citation-selection errors,
not truncation. The scope packet still lacks expected `4.1`–`4.3`, so it remains
evidence-limited and needs a separate retrieval fix.

The local artifacts are
`user_scoped_parent_explicit_vllm_bf16_20260813_072622` (baseline 10 packets) and
`bot_parent_explicit_full_child_json_contract_vllm_bf16_20260813_074325` (the 5-packet
renderer validation, including a Codex Sol answer review). Raw benchmark packets are not
republished here because this README reports the result summary only.

## Current official datasets

| Dataset | แหล่งข้อมูล | Retrieval corpus | Provenance |
|---|---|---:|---|
| พ.ร.บ. การประกอบธุรกิจข้อมูลเครดิต (NCB) | [BOT principal text Updated-2559](https://www.bot.or.th/content/dam/bot/documents/th/laws-and-rules/laws-and-regulations/legal-department/7-ncb-act/7-1-ncb-act/7.1.2-Law_TH_CreditBureau%20Updated-2559.pdf) | 9 parents + exactly 66 primary article children | official PDF pages 1–18; retrieve/cite at `มาตรา` only; 20/1 and 31/1 are incorporated into articles 20 and 31, not duplicate rows; repeating footer removed |
| BOT Digital Fraud Management | [BOT 2568/0254](https://www.bot.or.th/content/dam/bot/fipcs/documents/FPG/2568/ThaiPDF/25680254.pdf) | 6 parents + exactly 11 `X.X` children | official PDF pages 2–13; retrieve/cite at `X.X` only; deeper `X.X.X` content is grouped in its owning `X.X` child, never a separate retrieval/citation row |

NCB และ Digital Fraud เป็นการ extract ตัวบทให้แยกข้อกำหนดและ citation ได้ ไม่ใช่ scenario Q&A
จากเหตุการณ์จริง จึงควรวัดต่อกับโจทย์ข้อเท็จจริงที่หลากหลายก่อนใช้งานจริง

## Archived 15-question comparison — 12 August 2026

The following published NitiBench/NCB/Digital Fraud comparison is retained as a separate
historical run. Its corpus counts, screenshots, evidence packets, and metrics are not the
current parent-explicit official-dataset run above.

### วิธีทดสอบและ leakage controls

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

### ผลเชิงเทคนิคหลัง inference

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

### คุณภาพการเรียบเรียงภาษาไทย — Codex Sol blind review

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

### ไฟล์ผลลัพธ์ครบทุกข้อ ทุกโมเดล ทุก dataset

ผลที่เผยแพร่ถูกย่อให้มีเฉพาะคำถาม, evidence ที่คัดเลือก, คำตอบ, citation, เวลา, metric หลัง inference
และคะแนน blind language review ไม่มี raw prompt, reference answer หรือ expected-citation label

- [Manifest และขอบเขตไฟล์](results/three-model-benchmark-20260812/manifest.json)
- [ผลรวม 15 ข้อ / 3 โมเดล](results/three-model-benchmark-20260812/all_cases.json)
- [ผลรายข้อแยก 15 ไฟล์](results/three-model-benchmark-20260812/cases/)
- [Codex Sol blind language review (Markdown)](results/three-model-benchmark-20260812/language_blind_review.md)
- [Codex Sol blind language review (JSON)](results/three-model-benchmark-20260812/language_blind_review.json)

SHA-256 ของ source artifacts, จำนวน case และรายการไฟล์อยู่ใน manifest เพื่อให้ตรวจการแปลงผลได้

## ข้อจำกัด

- Current NCB/Digital Fraud comparison has only 10 fixed questions; it is neither a random
  sample nor a coverage measurement of either instrument.
- A long grouped child can be complete in the corpus yet incomplete in the model prompt. Fix
  prompt rendering or deterministically segment a long child while preserving its single
  `X.X` citation before treating the later nested requirements as available evidence.
- The Digital Fraud scope question must retrieve 4.1–4.3 before a complete scope answer can
  be evaluated.
- เป็น fixed benchmark 15 ข้อ ไม่ใช่ตัวอย่างสุ่มหรือการวัด coverage ของกฎหมายไทยทั้งหมด
- BF16 ใช้ frozen final evidence ชุดเดียวกับ Q4/Qwen; ยังไม่มีผลรอบ fresh retrieval ของ BF16
- เวลาแต่ละ run อยู่คนละ runtime/cache จึงไม่ควรใช้ตัดสิน production latency หรือ concurrency
- Citation metric ตรวจความสอดคล้องกับ label หลัง inference ไม่แทนการอ่านตัวบทหรือการตีความทางกฎหมาย
- ต้องเพิ่มโจทย์หลายมาตรา ข้อยกเว้น กฎหมายชื่อใกล้กัน และข้อเท็จจริงจริง พร้อม human review ก่อนใช้งาน
- repository นี้ไม่เก็บ model weights, credential, token หรือ chat session
