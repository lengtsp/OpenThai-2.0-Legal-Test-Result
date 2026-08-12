# OpenThai 2.0 Legal: ทดสอบ Thai Legal RAG ด้วย Ollama (Q4)

ผลทดสอบอิสระของ [OpenThai 2.0 Legal](https://huggingface.co/iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b)
ผ่าน Ollama Q4 เทียบกับ `Qwen3.6-35B-A3B` บน llama.cpp Q5

> ผลนี้เป็น **preliminary / unreviewed** ไม่ใช่คำแนะนำหรือคำวินิจฉัยทางกฎหมาย
> ก่อนใช้งานจริงต้องให้ผู้เชี่ยวชาญกฎหมายไทยตรวจตัวบทฉบับปัจจุบัน ข้อเท็จจริง และข้อยกเว้น

## สิ่งที่ทดสอบ

| Dataset | แหล่งข้อมูล | ขนาด corpus | การอ้างอิง |
|---|---|---:|---|
| NitiBench | [VISAI-AI/NitiBench](https://huggingface.co/datasets/VISAI-AI/nitibench) | 3,934 chunks | ระดับมาตรา; ไม่มี page field จาก source store |
| พ.ร.บ. การประกอบธุรกิจข้อมูลเครดิต พ.ศ. ๒๕๔๕ (NCB) | [BOT principal text Updated-2559](https://www.bot.or.th/content/dam/bot/documents/th/laws-and-rules/laws-and-regulations/legal-department/7-ncb-act/7-1-ncb-act/7.1.2-Law_TH_CreditBureau%20Updated-2559.pdf) | 225 units | 73 parent + 152 child; page-anchored; corpus ใช้งานจริงรวมฉบับแก้ไข 1–6 |
| Digital Fraud Management | [BOT 2568/0254](https://www.bot.or.th/content/dam/bot/fipcs/documents/FPG/2568/ThaiPDF/25680254.pdf) | 54 units | ระดับข้อ/ข้อย่อย พร้อมเลขหน้า |

PDF NCB จาก BOT ที่ระบุ `Updated-2559` ใช้เป็นเอกสารหลักสำหรับตรวจเทียบ แต่ยังไม่รวม
ฉบับที่ 6 ปี 2565 จึงไม่ใช้แทน corpus ฉบับรวม 1–6 และไม่สร้าง amendment-only dataset แยก

## Hybrid RAG ที่ใช้จริง

ทุกคำถามค้นเฉพาะ corpus ที่เลือกก่อน จึงไม่ปะปนหลักฐานคนละชุดข้อมูล

```text
คำถาม
  ├─ Dense retrieval
  ├─ Sparse / lexical retrieval
  ├─ Hybrid fusion (RRF หรือ parent/child hybrid ตาม corpus)
  ├─ BGE reranker
  └─ หลักฐาน 8 รายการ → โมเดลตอบ JSON พร้อม citation
```

| ขั้นตอน / parameter | ค่าที่ใช้ในการทดสอบ | หมายเหตุ |
|---|---|---|
| Embedding | Qwen3-Embedding-4B, 2,560 มิติ, L2-normalized | ใช้ข้อความตัวบทเท่านั้น |
| Candidate ก่อน rerank | 20 | จำกัดในแต่ละ corpus |
| NitiBench fusion | Milvus dense cosine + Thai BM25 + native RRF | จากนั้น BGE rerank |
| NCB fusion | parent/child hybrid + explicit-reference expansion | รักษา parent/child และมาตราที่อ้างถึง |
| Digital Fraud fusion | dense + Thai lexical RRF + explicit-reference closure | รักษา ข้อ/ข้อย่อย และเลขหน้า |
| Reranker | BGE-M3 cross-encoder | rerank หลักฐานก่อนส่งโมเดล |
| Final evidence (`top_k`) | 8 | ทั้งสองโมเดลรับ evidence ชุดเดียวกัน |
| Generation | temperature 0.0, top_p 1.0, max_tokens 2,048, seed 42, thinking off | JSON answer + citations |
| Leakage control | expected citation / เฉลย ใช้หลัง inference เท่านั้น | ไม่เข้า embedding, retriever, reranker หรือ prompt |

## ผลทดสอบ: 3 datasets × 5 คำถาม

การค้นคืนพบ expected citation ใน top-8 ครบ 15/15 ข้อ และ JSON parse ได้ครบทั้งสองโมเดล

| Dataset | Expected-citation recall<br>OpenThai / Qwen | Codex Sol source-grounded review<br>OpenThai / Qwen | เวลา end-to-end เฉลี่ย<br>OpenThai / Qwen |
|---|---:|---:|---:|
| NitiBench | 100% / 100% | 4 supported + 1 partial / 5 supported | 21.73s / 10.69s |
| NCB (รวมฉบับแก้ไข 1–6) | 100% / 100% | 3 supported + 2 partial / 5 supported | 18.85s / 7.70s |
| Digital Fraud | 70% / 100% | 3 supported + 2 partial / 5 supported | 21.18s / 8.83s |
| **รวม 15 ข้อ** | **90% / 100%** | **10 supported + 5 partial / 15 supported** | **20.58s / 9.07s** |

### สรุปผลที่ควรอ่าน

| หัวข้อ | ข้อสรุปจากรอบทดสอบนี้ |
|---|---|
| Retrieval | ทั้งคู่ใช้ evidence ชุดเดียวกันและ retrieval พบ expected citation ครบ 15/15 |
| การตอบจาก evidence | Qwen ทำได้ดีกว่าในชุด 15 ข้อนี้: supported 15/15 เทียบกับ OpenThai 10/15 |
| จุดที่ OpenThai พลาด | สลับ actor/หน้าที่, ละเงื่อนไขหลายส่วน, ตอบไม่ครบคำถามหลายส่วน, หรือ over-cite |
| เวลา | Qwen เร็วกว่ารอบนี้ แต่เป็น sequential run และคนละ runtime/quantization ไม่ใช่ production benchmark |

`supported` หมายถึงสาระสำคัญของคำตอบตามหลักฐานที่รับเข้า benchmark;
`partial` หมายถึงแก่นคำตอบมีหลักฐาน แต่ actor, เงื่อนไข, scope หรือส่วนสำคัญยังขาด/คลาดเคลื่อน

<details>
<summary>รายการ use case และผลรายข้อ — ซ่อนคำถาม คำตอบ และผลละเอียด</summary>

| Dataset | Case | Expected citation | OpenThai: citation / review | Qwen: citation / review |
|---|---|---|---|---|
| NitiBench | unlicensed futures market | 132 | 1.00 / supported | 1.00 / supported |
| NitiBench | orchard lease | 565 | 1.00 / supported | 1.00 / supported |
| NitiBench | minor adoption | 1598/26 | 1.00 / partial | 1.00 / supported |
| NitiBench | current account | 856 | 1.00 / supported | 1.00 / supported |
| NitiBench | limited-company shareholder | 1096 | 1.00 / supported | 1.00 / supported |
| NCB | owner dispute | 27 | 1.00 / partial | 1.00 / supported |
| NCB | disclosure consent | 20 | 1.00 / supported; over-citation | 1.00 / supported |
| NCB | correction deadline | 26 | 1.00 / supported | 1.00 / supported |
| NCB | rejection reasons | 28 | 1.00 / partial | 1.00 / supported |
| NCB | unlawful disclosure penalty | 51 | 1.00 / supported | 1.00 / supported |
| Digital Fraud | scope | 4 | 1.00 / supported; over-citation | 1.00 / supported |
| Digital Fraud | governance | 5.3.1, 5.3.1(2) | 0.50 / partial | 1.00 / supported |
| Digital Fraud | monitoring | 5.3.2(2), 5.3.2(2.1) | 0.50 / supported | 1.00 / supported |
| Digital Fraud | customer response | 5.3.2(4.2), 5.3.2(4.3) | 0.50 / partial | 1.00 / supported |
| Digital Fraud | reporting | 5.3.5 | 1.00 / supported | 1.00 / supported |

</details>

## ผลเสริม: PostgreSQL เทียบ Milvus

เป็น baseline NitiBench 5 ข้อแยกจากการเทียบโมเดลข้างต้น

| Metric | PostgreSQL hybrid RRF | Milvus native BM25 + RRF |
|---|---:|---:|
| Candidate recall@20 | 100% | 100% |
| Citation recall / precision | 100% / 100% | 100% / 100% |
| Exact citation set | 5/5 | 5/5 |
| Retrieval เฉลี่ย | 1.630s | 0.057s |
| End-to-end เฉลี่ย | 9.156s | 7.280s |

PostgreSQL ใช้ dense pgvector + FTS/pg_trgm + application RRF (`k=60`); Milvus ใช้ dense cosine + Thai 3/4-character n-gram BM25 + native RRF (`k=80`). เวลามาจากคนละ run/cache จึงใช้เปรียบเทียบเชิงสำรวจเท่านั้น

## ข้อจำกัด

- เป็น fixed benchmark 15 ข้อ ไม่ใช่ตัวอย่างสุ่มหรือ coverage ของกฎหมายไทยทั้งหมด
- Citation ตรง ไม่ได้หมายความว่าคำตอบเป็นคำวินิจฉัยทางกฎหมายที่ครบถ้วน
- Codex Sol เป็น independent model review ไม่ใช่ Thai legal-expert adjudication
- Repository นี้ไม่มี model weights, credential, token หรือ chat session
