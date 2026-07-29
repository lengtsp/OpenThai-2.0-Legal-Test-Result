# OpenThai 2.0 Legal — Independent Test Results

Repository นี้รวบรวมผลทดสอบอิสระของ
[`iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b`](https://huggingface.co/iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b)
ทั้งการตอบตรง, Legal essay, General chat และ RAG บนเครื่อง local ผ่าน vLLM
OpenAI-compatible API

การอัปเดตรอบล่าสุดนี้ไม่เพิ่ม model weights, API token, database credential,
chat session, raw answers หรือ scenario captures

## 1. โมเดลมาจากไหนและพัฒนาโดยใคร

OpenThai 2.0 Legal เป็นโมเดล open-weight ภาษาไทยด้านกฎหมาย พัฒนาโดยทีม
**OpenThai (AIEAT / iApp Technology)** บน NVIDIA NeMo stack โดยใช้ text core
ของ `NVIDIA Nemotron-3-Nano-Omni-30B-A3B-Reasoning` เป็น base model

| รายการ | รายละเอียดจาก model card |
|---|---|
| Architecture | Mamba2–Transformer hybrid MoE |
| Parameters | 30B รวม, ประมาณ 3B active ต่อ token |
| ภาษา | ไทยเป็นหลัก; reasoning ภาษาอังกฤษ |
| Served context | 32,768 tokens รวม prompt และ completion |
| Serving | vLLM และ NVIDIA NIM แบบ OpenAI-compatible |
| จุดเน้น | กฎหมายไทย การอ้างชื่อกฎหมาย/มาตรา และบทวิเคราะห์กฎหมาย |

ข้อมูลส่วนนี้เป็นการสรุปจาก
[model card ของผู้พัฒนา](https://huggingface.co/iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b)
ไม่ใช่ข้อค้นพบใหม่ของผู้ทดสอบ

## 2. บทบาทของผู้จัดทำ

ผู้จัดทำ repository เป็น **ผู้ทดสอบอิสระเท่านั้น** ไม่ใช่ผู้พัฒนา ผู้แทน
หรือผู้รับรองโมเดล การให้คะแนนเป็น `Codex-assisted evaluation` จาก scenario
และ checklist ที่ผู้ทดสอบจัดทำ จึงไม่ใช่ official benchmark และไม่ใช่
คำปรึกษากฎหมาย

การทดสอบเก็บ generation parameters, token usage, latency, `finish_reason`
และข้อผิดพลาดที่สังเกตได้ โดยไม่แก้คำตอบและไม่มี automatic retry

## 3. Recommended generation settings

รอบหลักยึดค่าที่ผู้พัฒนาแนะนำ แยกตามวัตถุประสงค์ ไม่ใช้ parameter ชุดเดียว
ตัดสินทุกงาน

| Use case | Temperature | Top-p | Max tokens | Thinking |
|---|---:|---:|---:|---:|
| Citation answering — RAG/closed-book | 0.0 | 1.0 | 2,048 | Off |
| Legal essay drafting | 0.7 | 0.9 | 4,096 | Off |
| Legal essay แบบ thinking | 0.7 | 0.9 | 6,144 | On |
| General chat | 0.7 | 0.9 | 2,048 | Off |

Citation answering ไม่ถูกรวมในคะแนนรอบล่าสุด เพราะเป็นงาน JSON citation
คนละประเภทกับบทความและแชต ผลรอบล่าสุดเรียงลำดับเป็น:

1. Legal essay drafting — Thinking Off
2. Legal essay — Thinking On
3. General chat — Thinking Off และใช้โจทย์อีกห้าข้อซึ่งไม่ซ้ำกับ Legal essay

## 4. สภาพแวดล้อมรอบล่าสุด

| รายการ | ค่า |
|---|---|
| วันที่ | 29 กรกฎาคม 2026 |
| GPU | NVIDIA RTX PRO 6000 Blackwell 96 GB |
| vLLM | 0.25.1 |
| Endpoint | `127.0.0.1:3033` |
| Served context | 32,768 tokens |
| Tensor parallel | 1 |
| Seed | 42 |
| RAG | ปิดสำหรับทั้งสามกลุ่ม |
| Requests | 15 |
| Automatic retries | 0 |

## 5. ผล Legal essay drafting — Thinking Off

ใช้ scenario กฎหมายไทยห้าประเภท: ประมาทร่วม, ดอกเบี้ยเงินกู้เกินอัตรา,
ลายมือชื่อผู้สั่งจ่ายเช็คปลอม, การทำลายเอกสาร และขอบเขต consent ข้อมูลเครดิต

| Metric | ผล |
|---|---:|
| Codex-assisted score | **61/120 (50.8%)** |
| เวลารวม | 376.64 วินาที |
| เวลาเฉลี่ย | 75.33 วินาที/ข้อ |
| Output tokens รวม | 10,759 |
| Output tokens เฉลี่ย | 2,151.8/ข้อ |
| Throughput | 28.57 tokens/วินาที |
| ถูกตัดด้วย token limit | 0/5 |

ข้อดีคือเขียนภาษาไทยเป็นระบบ จับประเด็นคู่กรณีได้ และไม่เปิดเผย reasoning
ภายใน แต่มีการแต่งเลขมาตรา สร้างสัดส่วนความรับผิดโดยไม่มีฐาน และคำนวณ
ค่าเสียหายสลับฝ่ายในบางข้อ

## 6. ผล Legal essay — Thinking On

ใช้โจทย์ Legal essay ชุดเดียวกับ Thinking Off เพื่อให้เปรียบเทียบได้โดยตรง

| Metric | ผล |
|---|---:|
| Codex-assisted score | **59/120 (49.2%)** |
| เวลารวม | 713.60 วินาที |
| เวลาเฉลี่ย | 142.72 วินาที/ข้อ |
| Output tokens รวม | 20,500 |
| Output tokens เฉลี่ย | 4,100/ข้อ |
| Throughput | 28.73 tokens/วินาที |
| ถูกตัดด้วย token limit | 0/5 |
| Reasoning ปรากฏใน API output | 5/5 |

Thinking ใช้เวลามากกว่า 89.5% และสร้าง tokens มากกว่า 90.5% แต่คะแนนไม่ได้
ดีขึ้น ในกรณีทำลายเอกสาร Thinking ระบุมาตรา 188 ได้ถูกกว่า Off แต่กลับ
วินิจฉัยว่าเป็นเพียงพยายาม ทั้งที่ holding อ้างอิงเป็นความผิดสำเร็จ

รอบนี้จึงเลือก **Thinking Off เป็นค่าเริ่มต้นสำหรับ Legal essay** เพราะเร็วกว่า
ไม่มี reasoning leakage และแม่นกว่าเล็กน้อย อย่างไรก็ตาม คะแนน 50.8%
ยังไม่เพียงพอให้ใช้ closed-book essay เป็นแหล่งยืนยันกฎหมาย

## 7. ผล General chat

General chat ใช้โจทย์คนละชุดกับ Legal essay ได้แก่ เงินประกันห้องเช่า,
ซื้อของออนไลน์, ค่าล่วงเวลา, เงินกู้ผ่าน Line และหมายเรียกพยาน

| Metric | ผล |
|---|---:|
| Codex-assisted score | **69/100 (69.0%)** |
| เวลารวม | 221.49 วินาที |
| เวลาเฉลี่ย | 44.30 วินาที/ข้อ |
| Output tokens รวม | 6,547 |
| Output tokens เฉลี่ย | 1,309.4/ข้อ |
| Throughput | 29.56 tokens/วินาที |
| ถูกตัดด้วย token limit | 1/5 |

โมเดลช่วยจัดรายการหลักฐานและขั้นตอนเบื้องต้นได้ดี แต่ยังมีความเสี่ยงจากการ
ระบุหน่วยงานผิด เหมารวมสิทธิ OT ของลูกจ้างรายเดือน และสรุปว่าการอ่านข้อความ
แล้วไม่ตอบเป็นการยอมรับหนี้ General chat จึงเหมาะกับ triage มากกว่าการยืนยัน
ข้อกฎหมายเฉพาะ

## 8. ข้อสรุปและค่าที่เลือก

| งาน | ค่าที่เลือกหลังรอบนี้ | เหตุผล |
|---|---|---|
| Legal essay | `temp=0.7`, `top_p=0.9`, `max_tokens=4096`, Thinking Off | เร็วกว่า ไม่มี reasoning leakage และคะแนนสูงกว่าเล็กน้อย |
| General chat | `temp=0.7`, `top_p=0.9`, `max_tokens=2048`, Thinking Off พร้อมสั่งให้ตอบกระชับ | ตรง official profile; ลดโอกาสชนเพดานด้วย prompt ก่อนเพิ่ม token |
| Citation/RAG | `temp=0`, `top_p=1`, `max_tokens=2048`, Thinking Off | ใช้ JSON citation contract และ focused statutory context |

งานที่ต้องอ้างเลขมาตรา ควร retrieve ตัวบทที่เกี่ยวข้องแบบหนึ่งมาตราต่อหนึ่ง
chunk แล้วตรวจ citations ก่อนส่งให้ Legal essay เรียบเรียงอีกชั้น

รายงานฉบับเต็มที่ไม่มีคำตอบดิบ:

- [Three-generation-profile evaluation](reports/OPENTHAI_THREE_GENERATION_PROFILES_20260729.md)

## 9. ผลงาน RAG และเครื่องมือก่อนหน้า

### 9.1 NCB structural RAG benchmark and Open WebUI

The official consolidated Credit Information Act PDF was parsed by legal
structure rather than fixed windows. The current v2 Open WebUI package contains
73 active sections, one complete `มาตรา` per clean `<law>` file. PDF page
anchors and source hashes stay in metadata; amendment-history appendices and
superscript note markers are excluded from effective model context.

Thirteen NCB scenarios were tested across access logging, consent, loan brokers, correction/dispute, adverse decisions, definitions, licensing, data lifecycle, member reporting, confidentiality, credit models, penalties, and unlawful disclosure.

| Evidence mode | Scenarios | Relevant citation result |
|---|---:|---:|
| Exact structural sections | 13 | **100% precision / 100% recall** |
| Dense Qwen embedding top-4 — original five | 5 | 40.0% precision / 66.7% recall |
| Dense Qwen embedding top-4 — extended eight | 8 | 51.0% precision / 81.2% recall |

The result shows that OpenThai performs strongly when supplied the correct complete sections. Production retrieval should combine BM25 and Qwen embeddings, deduplicate by legal section, rerank, and inject the smallest complete evidence set while retaining every section explicitly requested by the user.

Start the hardened local Open WebUI profile at `127.0.0.1:3000` with [the
supplied Compose file](openwebui_3000/docker-compose.yml). It connects OpenThai
at port `3033`, Qwen3-Embedding-4B at port `8082`, retrieves 12 hybrid
candidates, reranks to 8, and keeps the model context free of repeated YAML,
filenames, and source URLs.

The final live Open WebUI run used an 8,192-token vLLM context, a 2,048-token
answer cap, and `enable_thinking=false`. All five audit answers completed with
`finish_reason=stop` (580–1,213 generated tokens); the largest observed
prompt-plus-answer was 5,015 tokens. Mean retrieval/chat times were
12.42s/41.80s. Hybrid top-3 retrieval reached 46.7% macro precision and 63.3%
macro recall, so answer truncation is fixed while multi-section retrieval
remains the primary improvement target.

The additional long-context run expanded vLLM to 12,288 tokens and reserved
4,096 output tokens. Four exact-evidence audit scenarios used 5,815–9,698 total
tokens and all returned `finish_reason=stop`. Citation precision/recall reached
89.7%/96.4%, but substantive Codex judging averaged only 2.38/5 because the
answers still invented deadlines, notification duties, sample sizes, and legal
effects. The 12k context solves capacity; it does not replace claim validation
or human legal review.

The current default is now the documented iApp JSON citation path:
`temperature=0`, `top_p=1`, `max_tokens=2048`, thinking off, the trained
OpenThaiGPT-Legal system contract, and user-injected `Provided context` with
`<law law_name="..." section="...">`. A live access-log test returned valid
JSON, cited only section 17, and correctly stated the two-year minimum. An
adverse-decision test still transferred a 30-day right-exercise window into a
bank deadline, so parameter/chunk alignment does not replace claim-level
validation or human legal review.

Key resources:

- [Structural chunk tutorial](reports/STRUCTURAL_CHUNK_NCB_TUTORIAL.md)
- [Extended NCB benchmark](reports/NCB_OPENTHAI_EXTENDED_RAG_BENCHMARK.md)
- [Open WebUI and RAG test report](reports/CREDIT_INFO_ACT_NCB_OPENWEBUI_RAG_TEST.md)
- [Live Open WebUI 8,192/2,048 benchmark](openwebui_ncb_live_test_8192_2048_20260729/report.md)
- [1,024-token truncation control](openwebui_ncb_live_test_8192_20260729/report.md)
- [OpenThai 12,288/4,096 long-context benchmark](openthai_12k_long_context_20260729/report.md)
- [OpenThai 12k controlled parameter sweep](openthai_parameter_sweep_12k_20260729/report.md)
- [`$extract-structural-legal-chunks` reusable skill](skills/extract-structural-legal-chunks/SKILL.md)
- [73 clean iApp-compatible section files](data/credit_info_act/openwebui_knowledge_v2/README.md)

### 9.2 NCSA page-grounded RAG benchmark — OpenThai2.0 vs Qwen3.6-27B

This evaluation has two layers against a 629-page NCSA cyber-security compendium. The original 10-scenario run uses BM25-retrieved chunks; the newer **controlled 7-scenario rerun** locks the exact evidence chunks per question, so retrieval quality cannot obscure synthesis/citation quality. Codex reviewed each answer against its supplied source chunks.

| Metric | OpenThai2.0 Legal | Qwen3.6-27B | Outcome |
|---|---:|---:|---|
| Controlled mean model-request latency | 21.60 s | **19.33 s** | Qwen faster by **10.5%** |
| Controlled strict `[p.x c.y]` citation syntax | 4/7 | **7/7** | Qwen stronger |
| Controlled Codex concept coverage | 25/26 | **26/26** | Both grounded; Qwen more consistent |

The comparison is an operational RAG replay rather than a pure model-quality study: OpenThai used vLLM and Qwen used llama.cpp with a Q8 GGUF build. Model loading is excluded from latency metrics. The controlled result is the primary comparison; see [the controlled report](reports/NCSA_CONTROLLED_FIXED_EVIDENCE_BENCHMARK.md). The earlier retrieval-inclusive result is retained in [the original NCSA report](reports/NCSA_OPENTHAI_VS_QWEN36_27B_BENCHMARK.md).

## 10. Repository contents

- `web/rag_webui_8083/` — browser UI and Python service on port `8083`
- `web/rag_webui_8083/data/legal_corpus.json` — five BOT evaluation chunks with source URLs
- `reports/BOT_RAG_EVALUATION_20260729.md` — eight BOT-grounded test scenarios and findings
- `reports/INFERENCE_RAG_TEST_REPORT.md` — initial model/inference measurements
- `reports/RAG_WEBUI_8083.md` — architecture and API notes
- `reports/NCSA_OPENTHAI_VS_QWEN36_27B_BENCHMARK.md` — NCSA recursive-chunk replay, latency comparison, and Codex judge rubric
- `reports/NCSA_CONTROLLED_FIXED_EVIDENCE_BENCHMARK.md` — primary controlled rerun with locked evidence per scenario
- `reports/STRUCTURAL_CHUNK_NCB_TUTORIAL.md` — hands-on Thai legal structural chunking guide
- `reports/NCB_OPENTHAI_EXTENDED_RAG_BENCHMARK.md` — eight additional NCB scenarios
- `openwebui_3000/` — Open WebUI v0.9.5 profile for OpenThai + Qwen embeddings
- `skills/extract-structural-legal-chunks/` — reusable validated Codex skill and extractor
- `data/credit_info_act/openwebui_knowledge_v2/` — clean current-law `<law>` section files ready for Knowledge upload

## 11. Run locally

Start an OpenAI-compatible vLLM server first. The example UI expects it at `127.0.0.1:3033` and uses the served model name `openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b`.

The RAG UI persists chat sessions in PostgreSQL. Create a database named `opengpt` and set its connection values only in your shell or deployment secret store:

```bash
export OPENGPT_DB_HOST=127.0.0.1
export OPENGPT_DB_PORT=5432
export OPENGPT_DB_NAME=opengpt
export OPENGPT_DB_USER='your_user'
export OPENGPT_DB_PASSWORD='your_password'
python3 web/rag_webui_8083/server.py
```

Open `http://localhost:8083`.

The service needs Python `psycopg2` for PostgreSQL session persistence. It has no frontend build step.

## 12. BOT source boundary

The corpus is a small evaluation set, not a complete legal/regulatory database. Verify any answer against the linked primary source and current official notices. See the BOT evaluation report for observed limitations, especially citation compliance in synthesis answers.
