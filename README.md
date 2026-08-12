# ทดสอบ OpenThai 2.0 Legal สำหรับ Thai Legal RAG ด้วย Ollama (Q4)

รายงานการทดสอบอิสระของ
[OpenThai 2.0 Legal](https://huggingface.co/iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b)
เมื่อใช้ตอบคำถามกฎหมายไทยแบบ RAG ผ่าน Ollama Q4 เทียบกับ
`Qwen3.6-35B-A3B` บน llama.cpp Q5

ผู้จัดทำเป็นผู้ทดสอบอิสระ ไม่เกี่ยวข้องกับผู้พัฒนาโมเดล ผลทั้งหมดเป็น
**preliminary / unreviewed** ไม่ใช่คำแนะนำหรือคำวินิจฉัยทางกฎหมาย
ก่อนนำไปใช้จริงต้องให้ผู้เชี่ยวชาญกฎหมายไทยตรวจตัวบทฉบับปัจจุบัน ข้อเท็จจริง และข้อยกเว้น

## เว็บสำหรับทดลองใช้

เว็บ local `rag_webui_8083` ใช้เลือกชุดข้อมูล สนทนา และเปิดตารางคลังข้อมูลได้

- เลือก NitiBench, พ.ร.บ. NCB, Digital Fraud หรือรวมทุกชุด
- แสดง source, score, page index และ parent/child provenance ของหลักฐาน
- มีประวัติแชทและ use case ที่เปลี่ยนตาม dataset
- เปิด Dataset table แยกจากหน้าสนทนาเพื่อดู record/chunk ได้

## ชุดข้อมูลที่ใช้

| Dataset | แหล่งข้อมูล | Corpus ที่ทดสอบ | Provenance |
|---|---|---:|---|
| NitiBench | [VISAI-AI/NitiBench](https://huggingface.co/datasets/VISAI-AI/nitibench) | 3,934 legal chunks | Passage embedding ใช้เฉพาะตัวบทกฎหมาย ไม่รวมคำตอบหรือเฉลย |
| พ.ร.บ. การประกอบธุรกิจข้อมูลเครดิต (NCB) | [BOT principal text Updated-2559](https://www.bot.or.th/content/dam/bot/documents/th/laws-and-rules/laws-and-regulations/legal-department/7-ncb-act/7-1-ncb-act/7.1.2-Law_TH_CreditBureau%20Updated-2559.pdf) | 225 units: 73 parent + 152 child | corpus ใช้งานจริงเป็นฉบับรวมแก้ไข 1–6 หนึ่งชุด ไม่แยก amendment-only dataset |
| Digital Fraud Management | [แนวนโยบาย BOT 2568/0254](https://www.bot.or.th/content/dam/bot/fipcs/documents/FPG/2568/ThaiPDF/25680254.pdf) | 54 units | แยกตามข้อ/ข้อย่อย พร้อมเลขหน้า |

ไฟล์ NCB จาก BOT ที่ระบุว่า Updated-2559 เป็นเล่มหลักรวมถึงปี 2559 และไม่รวมฉบับที่ 6
ปี 2565 จึงใช้เป็นเอกสารตรวจเทียบ แต่ไม่แทน corpus ฉบับรวม 1–6 ที่ใช้ตอบจริง
การเทียบมาตรา 20, 26–28 และ 51 ยืนยันว่า 5 use cases NCB ในรายงานยังตรงกับสาระหลัก
โดยมาตรา 51 ของชุดรวม 1–6 เพิ่มขอบเขตอ้างถึงมาตรา 24/1 แต่โทษสูงสุดไม่เปลี่ยน

## แนวทางทดสอบ

ใช้คำถามคงที่ 15 ข้อ: dataset ละ 5 ข้อ ทั้งสองโมเดลได้รับ evidence ชุดเดียวกัน
จึงวัดการสังเคราะห์คำตอบและ citation หลัง retrieval ได้เป็นธรรม

```text
คำถาม
  ├─ Dense: Qwen3-Embedding-4B, 2,560 มิติ, L2-normalized
  ├─ Sparse: lexical / Thai n-gram retrieval
  └─ Hybrid fusion + rerank
                ↓
      top_k = 8 evidence ชุดเดียวกัน
                ↓
  OpenThai Q4         Qwen3.6-35B-A3B Q5
                ↓
     JSON answer + grounded citations
                ↓
  ให้คะแนน expected citation หลัง inference เท่านั้น
```

`expected citation`, คำตอบอ้างอิง และเฉลยไม่ถูกส่งเข้า embedding, retriever, reranker
หรือ prompt ของโมเดล ใช้เฉพาะเพื่อให้คะแนนหลังโมเดลตอบแล้ว

| Parameter | Value |
|---|---:|
| retrieval top_k | 8 |
| embedding | Qwen3-Embedding-4B, 2,560 dimensions |
| temperature / top_p | 0.0 / 1.0 |
| max_tokens | 2,048 |
| seed | 42 |
| output | JSON answer + citation |

## สรุปผล 3 datasets × 5 questions

รอบทดสอบสมบูรณ์ 15/15 ข้อ ทุกข้อ retrieval พบ expected citation ใน top-8
และทั้งสองโมเดลส่ง JSON ที่ parse ได้ครบ 15/15 ข้อ

| Dataset | Expected-citation recall OpenThai / Qwen | Codex Sol source-grounded review OpenThai / Qwen | เวลา end-to-end เฉลี่ย OpenThai / Qwen |
|---|---:|---:|---:|
| NitiBench | 100% / 100% | 4 supported + 1 partial / 5 supported | 21.73s / 10.69s |
| NCB (full 1–6) | 100% / 100% | 3 supported + 2 partial / 5 supported | 18.85s / 7.70s |
| Digital Fraud | 70% / 100% | 3 supported + 2 partial / 5 supported | 21.18s / 8.83s |
| **รวม 15 ข้อ** | **90% / 100%** | **10 supported + 5 partial / 15 supported** | **20.58s / 9.07s** |

Codex Sol อ่านคำตอบจริง 30 คำตอบเทียบกับตัวบทที่รับเข้า benchmark โดยแยกจาก metric
อัตโนมัติ จึงตรวจพบการสลับผู้มีหน้าที่ การละเงื่อนไขหลายส่วน และการอ้างบทที่อยู่ใกล้เคียง
แม้ citation จะ grounded แล้ว

> เวลาเป็นการรัน sequential บนเครื่องเดียวกัน ไม่ใช่ production latency หรือ concurrency benchmark

<details>
<summary>รายการทดสอบ ผลรายข้อ และขอบเขตการตรวจ — ซ่อนคำถาม/คำตอบ/ผลละเอียด</summary>

| Dataset | Case | Expected citation | OpenThai: citation / review | Qwen: citation / review |
|---|---|---|---|---|
| NitiBench | unlicensed futures market | 132 | 1.00 / supported | 1.00 / supported |
| NitiBench | orchard lease | 565 | 1.00 / supported | 1.00 / supported |
| NitiBench | minor adoption | 1598/26 | 1.00 / partially supported | 1.00 / supported |
| NitiBench | current account | 856 | 1.00 / supported | 1.00 / supported |
| NitiBench | limited company shareholder | 1096 | 1.00 / supported | 1.00 / supported |
| NCB | owner dispute | 27 | 1.00 / partially supported | 1.00 / supported |
| NCB | disclosure consent | 20 | 1.00 / supported; over-citation | 1.00 / supported |
| NCB | correction deadline | 26 | 1.00 / supported | 1.00 / supported |
| NCB | rejection reasons | 28 | 1.00 / partially supported | 1.00 / supported |
| NCB | unlawful disclosure penalty | 51 | 1.00 / supported | 1.00 / supported |
| Digital Fraud | scope | 4 | 1.00 / supported; over-citation | 1.00 / supported |
| Digital Fraud | governance | 5.3.1, 5.3.1(2) | 0.50 / partially supported | 1.00 / supported |
| Digital Fraud | monitoring | 5.3.2(2), 5.3.2(2.1) | 0.50 / supported | 1.00 / supported |
| Digital Fraud | customer response | 5.3.2(4.2), 5.3.2(4.3) | 0.50 / partially supported | 1.00 / supported |
| Digital Fraud | reporting | 5.3.5 | 1.00 / supported | 1.00 / supported |

`supported` คือสาระสำคัญของคำตอบตามหลักฐานที่รับเข้า benchmark;
`partially supported` คือมีหลักฐานรองรับแก่นคำตอบ แต่ขาด/สลับ actor/เงื่อนไข/
ขอบเขต citation ที่เป็นสาระสำคัญ ไม่มีคำตอบระดับ unsupported ในรอบนี้

</details>

## ทำไม citation ตรง แต่คำตอบยังไม่ครบได้

OpenThai ดึงหลักฐานที่ถูกต้องได้ดี แต่คำตอบที่เป็น `partially supported` พบรูปแบบต่อไปนี้:

- สลับผู้มีหน้าที่กับผู้มีสิทธิอุทธรณ์
- เปลี่ยนความถี่หรือเงื่อนไขของข้อกำหนด
- ตอบเพียงด้านเดียวของคำถามที่ต้องครอบคลุมหลายหน้าที่
- อ้างมาตราข้างเคียงหลายมาตรา ทั้งที่มาตราหลักเพียงมาตราเดียวรองรับข้ออ้าง

ดังนั้น metric retrieval/citation ต้องรายงานแยกจาก source-grounded answer review

## ผลเสริม: PostgreSQL และ Milvus

<details>
<summary>Baseline NitiBench 5 ข้อของ retrieval backend</summary>

| Metric | PostgreSQL hybrid RRF | Milvus native BM25 + RRF |
|---|---:|---:|
| candidate recall@20 | 100% | 100% |
| citation recall / precision | 100% / 100% | 100% / 100% |
| exact citation set | 5/5 | 5/5 |
| retrieval เฉลี่ย | 1.630s | 0.057s |
| end-to-end เฉลี่ย | 9.156s | 7.280s |

PostgreSQL ใช้ dense pgvector + FTS/pg_trgm + application RRF (`k=60`);
Milvus ใช้ dense cosine + Thai 3/4-gram BM25 + native RRF (`k=80`).
เวลาเป็นคนละ run/cache จึงไม่ใช่การรับประกัน performance ใน production

</details>

## ข้อจำกัดและขอบเขต human review

- เป็น fixed benchmark 15 ข้อ ไม่ใช่ตัวอย่างสุ่มหรือ coverage ของกฎหมายไทยทั้งหมด
- Expected citation ตรง ไม่เท่ากับคำวินิจฉัยทางกฎหมายถูกต้องครบถ้วน
- Codex Sol เป็น independent model review ไม่ใช่ Thai legal-expert adjudication
- ต้องทดสอบคำถามหลายมาตรา ข้อยกเว้น และข้อเท็จจริงจริงเพิ่มเติมก่อนใช้งาน
- repository นี้ไม่เก็บ model weights, credential, access token หรือ chat session
