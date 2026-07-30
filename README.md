# OpenThai 2.0 Legal — Independent Test Results

Repository นี้เก็บผลทดสอบอิสระของ
[`OpenThai 2.0 Legal`](https://huggingface.co/iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b)
ที่รันผ่าน vLLM แบบ OpenAI-compatible บนเครื่อง local ผู้จัดทำเป็นผู้ทดสอบ
ไม่ใช่ผู้พัฒนา ผู้แทน หรือผู้รับรองโมเดล

## ทดสอบประเด็นใดบ้าง

| กลุ่มการทดสอบ | สิ่งที่ดู | ข้อสรุปย่อ |
|---|---|---|
| การตอบกฎหมายจากความจำ | Closed-book Thai-law questions | ใช้ดูความสามารถจาก weights แต่ไม่ควรใช้แทนตัวบทปัจจุบัน |
| RAG กับกฎหมายไทย | Echo, Selection, retrieval และ citation | ควรใช้ RAG เป็นค่าเริ่มต้น; ต้องวัด retrieval และตรวจ citation แยกจากกัน |
| การเขียนบทวิเคราะห์ | Legal essay และ General chat | ช่วยร่างภาษาไทยได้ แต่ต้องตรวจมาตราและข้อสรุปโดยผู้เชี่ยวชาญ |
| NCB / PDPA / กฎหมายตลาดทุน / ข่าวสมมติ | Scenario เชิงปฏิบัติและ ground truth ที่เตรียมแยก | ใช้ตรวจข้อจำกัดของ prompt, chunks และการอ้างอิง ไม่ใช่คำวินิจฉัยทางกฎหมาย |

## ภาพรวมผล

- **ผลล่าสุดของ advanced hybrid RAG**: NitiBench retrieval 115 คำถามได้
  hit rate 92.17% ที่ `k=20`; open-book echo citation ถูก 9/9 แต่
  advanced selection จาก 10 candidates ถูกครบทั้ง recall/precision 5/9
  แสดงว่า selection หลัง retrieval ยังเป็นจุดเสี่ยง
- **NCB focused RAG หลัง optimize**: candidate recall 100%, OpenThai
  reranker recall 91.03% และชุด focused generation 5 scenarios อ้างมาตรา
  ครบและไม่เกินหลักฐาน 5/5
- **RAG สำคัญกว่าการพึ่ง Closed-book**: เมื่อมีตัวบทที่ถูกต้อง โมเดลตอบตาม evidence ได้ดีขึ้น; เมื่อไม่มี context อาจอ้างมาตราผิดหรือไม่ครบ
- **Chunk ต้องแบ่งตามมาตรา**: `law_name` + `section` และข้อความของมาตราเป็นรูปแบบที่ตรงกับคำแนะนำผู้พัฒนาและเอื้อต่อการตรวจ citation
- **Selection เป็นจุดเสี่ยง**: มีหลักฐานหลายมาตราที่คล้ายกันแล้วโมเดลยังเลือกเกิน/ตกหล่นได้ จึงต้องมี retriever ที่ดี, output validator และ human review
- **NCB controlled evidence รอบล่าสุด**: เมื่อส่ง focused evidence packet เดียวกัน OpenThai และ Qwen อ้างมาตราครบ 5/5 เท่ากัน ความต่างจากรอบเก่าจึงเกิดจาก retrieval/evidence selection มากกว่าความสามารถของ generator เพียงอย่างเดียว
- **อย่าดูคะแนนรวมเพียงค่าเดียว**: ผล retrieval แตกต่างมากตามกลุ่มกฎหมาย จึงรายงานแยก CCL, Tax และ scenario สำคัญ

ผลทั้งหมดเป็น **decision-support evaluation ไม่ใช่คำแนะนำกฎหมาย** และทุกมาตราต้องตรวจเทียบตัวบทฉบับปัจจุบันก่อนใช้งานจริง

## Highlight: จาก recursive chunks สู่ focused legal RAG

ผลที่ดีขึ้นไม่ได้เกิดจากการเพิ่ม `top_k` หรือเปลี่ยน schema เพียงอย่างเดียว
แต่เกิดจากการแก้ทั้ง **ขอบเขต chunk → metadata/provenance → retrieval →
rerank → evidence selection → citation validation** ตามลำดับ

### ก่อนปรับ: chunk อ่านได้ แต่ไม่ตรงหน่วยกฎหมาย

โครงการเคยใช้ PyMuPDF ตัดเอกสารรวมกฎหมายความมั่นคงปลอดภัยไซเบอร์
629 หน้าเป็น recursive chunks ขนาด 1,200 ตัวอักษร overlap 250 รวม
1,497 chunks วิธีนี้เหมาะกับการค้นข้อความทั่วไป แต่มีข้อจำกัดสำหรับคำตอบ
ที่ต้องอ้างข้อ/มาตรา:

- ขอบเขต chunk อาจเริ่มหรือจบกลางมาตรา และหนึ่ง chunk อาจมีหลายประเด็น
- header/footer, เชิงอรรถ และประวัติแก้ไขอาจปนกับเนื้อหาหลัก
- เลขมาตรากับข้อความอาจอยู่คนละ chunk ทำให้ citation traceability ลดลง
- ใน benchmark รุ่นนั้น OpenThai ทำ strict page/chunk citation ได้ 5/10
  แต่ผลดังกล่าวมาจากคนละเอกสารและคนละ test contract จึงใช้เป็นเพียง
  หลักฐานของข้อจำกัดด้าน traceability ไม่ใช่การเทียบก่อน–หลังโดยตรง

สำหรับ พ.ร.บ. ข้อมูลเครดิต ปัญหา extraction ที่พบจริงยิ่งเฉพาะเจาะจงกว่า:
plain text อาจอ่าน `มาตรา ๒` ที่มีเชิงอรรถ `๑` ติดกันเป็น `มาตรา ๒๑`
หรืออ่าน `มาตรา ๒๔/๑` กับเชิงอรรถ `๑๙` เป็น `มาตรา ๒๔/๑๑๙`
และอาจนำเชิงอรรถท้ายหน้าไปต่อท้าย body ของมาตราผิดแห่ง

### ระยะกลาง: one-section chunks ทำให้ data contract ดีขึ้น แต่ retrieval ยังพลาด

NCB Open WebUI v2 เปลี่ยนเป็นหนึ่งมาตราปัจจุบันต่อหนึ่งไฟล์ 73 records
และต่อมา project เป็น record แบบ NitiBench-compatible โดยฝัง
`law_name`, `section_num`, `section_content`, หน้า, source และ hash ไว้
ใน record เดียว:

```json
{
  "law_name": "พระราชบัญญัติการประกอบธุรกิจข้อมูลเครดิต พ.ศ. 2545",
  "section_num": "24",
  "section_content": "มาตรา ๒๔ ...ข้อความครบทั้งมาตรา...",
  "page_start": 9,
  "page_end": 9,
  "structural_path": ["หมวด ๓", "มาตรา ๒๔"],
  "source_url": "official-source",
  "content_hash": "sha256..."
}
```

ผลที่วัดได้:

| การทดสอบ NCB | ผล |
|---|---:|
| ส่ง exact structural sections ให้โมเดล | citation precision/recall 100% |
| Dense embedding top-4 | precision 40.0%, recall 66.7% |
| Dense top-4 ในชุดขยาย 8 scenario | exact citation เพียง 1/8 |
| แปลง Open WebUI v2 เป็น NitiBench-compatible แล้ววัด top-5 | macro recall 0.667 → 0.750 |

การเพิ่มจาก 0.667 เป็น 0.750 เป็นผลบวกขนาดเล็กในเพียง 6 queries และ
ขึ้นลงไม่เหมือนกันทุกข้อ ที่สำคัญ ทั้ง format เดิมและใหม่ยังหา
มาตรา 24 และ 54 ไม่พบในกรณีพนักงานทำข้อมูลเครดิตรั่วไหล จึงสรุปได้ว่า
**structural chunking ทำให้ evidence ที่ถูกต้องมีคุณภาพและตรวจสอบง่าย
แต่ไม่ได้รับประกันว่า dense retriever จะค้น evidence นั้นเจอ**

### หลังปรับ: structural chunks + advanced hybrid + focused evidence

รูปแบบที่ให้ผลดีที่สุดในรอบล่าสุดคือ:

```text
หนึ่งมาตราต่อหนึ่ง chunk
  → Dense + BM25 + FTS5 trigram
  → quota-preserving union, candidate 32
  → Thai legal/actor-aware query expansion
  → เชื่อมมาตราหน้าที่กับมาตราบทลงโทษ
  → OpenThai rerank top 10
  → focused evidence 2–6 chunks
  → Citation answer
  → ตรวจว่า citation ทุกตัวอยู่ใน evidence
```

ผล NCB 13 scenarios หลัง optimize มี candidate recall **100%** และ
OpenThai reranker recall **91.03%** ส่วน focused generation 5 scenarios
อ้างมาตราครบและไม่เกิน evidence **5/5** เทียบกับ dense-only ที่เคยพลาด
กรณีมาตรา 24/54 โดยตรง

#### Pattern ของ chunk ที่ควรใช้

1. หนึ่งมาตราที่มีผลใช้บังคับต่อหนึ่ง chunk; แบ่งเฉพาะมาตราที่ยาวเกิน
   limit และคง `section_id`, `part`, `parts` เพื่อประกอบกลับก่อนตอบ
2. เก็บข้อความต้นฉบับที่เริ่มด้วย canonical heading พร้อม `law_name`,
   `section`, หมวด, หน้า, source URL, effective date และ content hash
3. แปลงเลขไทย/อารบิกและคำค้นพ้องใน **index text** แต่ไม่เขียนทับ
   ข้อความตัวบทต้นฉบับ
4. แยกประวัติแก้ไขและมาตราซ้ำในภาคผนวกออกจาก active-law corpus
5. เก็บ cross-reference เช่น “หน้าที่/ข้อห้าม → บทกำหนดโทษ” เป็น
   relation สำหรับ retrieval expansion
6. ก่อน embedding ต้องตรวจ section ซ้ำ/หาย, footnote-only chunk,
   OCR noise, หน้าไม่ครบ และ cross-reference ที่ถูกเข้าใจผิดเป็นหัวมาตรา

รายละเอียด extraction และ quality gates อยู่ใน
[คู่มือ Structural Chunk สำหรับ NCB](reports/STRUCTURAL_CHUNK_NCB_TUTORIAL.md)
ส่วนตัวเลข retrieval/generation รอบล่าสุดอยู่ใน
[Advanced Hybrid RAG Evaluation](reports/advanced-hybrid-rag-20260729/README.md)

### ตัวอย่างคำถามและคำตอบที่อ้างจาก RAG

**คำถาม**

> ธนาคารในฐานะผู้ใช้บริการของบริษัทข้อมูลเครดิต ได้รับรายงานข้อมูลเครดิต
> จาก NCB เพื่อวิเคราะห์สินเชื่อบ้าน แต่กลับนำรายงานไปใช้คัดเลือกลูกค้า
> เพื่อทำการตลาดประกันและเปิดเผยแก่บริษัทประกันในเครือที่ไม่มีสิทธิรับรู้
> การนำข้อมูลไปใช้นอกวัตถุประสงค์และเปิดเผยเช่นนี้ฝ่าฝืนหน้าที่ของ
> ผู้ใช้บริการหรือไม่ และผู้ใช้บริการมีบทลงโทษอย่างไร

คำถามนี้กำหนด actor เป็น **ธนาคารในฐานะผู้ใช้บริการ NCB** และถามการใช้/
เปิดเผยรายงานเครดิตของ NCB โดยตรง จึงไม่ปนกับหน้าที่ของบริษัทข้อมูลเครดิต
ผู้ประมวลผล หรือพนักงานเป็นรายบุคคล ระบบค้น candidate 32 รายการ,
OpenThai rerank เหลือ 6 และเชื่อมมาตราหน้าที่กับบทลงโทษ ก่อนส่ง focused
evidence เพียง **มาตรา 22 หน้า 9** และ **มาตรา 52 หน้า 18** ให้ตอบด้วย
`temperature=0`, `top_p=1`, `max_tokens=2,048`, thinking off

**คำตอบจาก live benchmark**

> การนำข้อมูลไปใช้นอกวัตถุประสงค์และเปิดเผยแก่ผู้ไม่มีสิทธิรับรู้ข้อมูล
> เป็นการฝ่าฝืนหน้าที่ของผู้ใช้บริการตามมาตรา 22 แห่งพระราชบัญญัติ
> การประกอบธุรกิจข้อมูลเครดิต พ.ศ. 2545 ซึ่งมีบทลงโทษตามมาตรา 52
> โดยต้องระวางโทษจำคุกตั้งแต่ห้าปีถึงสิบปี หรือปรับไม่เกินห้าแสนบาท
> หรือทั้งจำทั้งปรับ
>
> อ้างอิงหลักฐานที่ใช้: [1] พระราชบัญญัติการประกอบธุรกิจข้อมูลเครดิต
> พ.ศ. ๒๕๔๕ (รวมฉบับแก้ไข ๑-๖) มาตรา 22 · p.9; [2] พระราชบัญญัติ
> การประกอบธุรกิจข้อมูลเครดิต พ.ศ. ๒๕๔๕ (รวมฉบับแก้ไข ๑-๖)
> มาตรา 52 · p.18

ผล live test ใช้เวลา **13.04 วินาที** และ citation set ตรง expected
sections 22/52 ทั้ง recall และ precision ตัวบททางการรองรับว่า
มาตรา 22 กำหนดหน้าที่ของผู้ใช้บริการให้ใช้ข้อมูลตามวัตถุประสงค์และ
ไม่เปิดเผยแก่ผู้ไม่มีสิทธิ ส่วนมาตรา 52 กำหนดโทษเมื่อผู้ใช้บริการฝ่าฝืน
มาตรา 22 อย่างไรก็ดี การใช้กับเหตุการณ์จริงยังต้องตรวจฐานะของแต่ละฝ่าย
ขอบเขตความยินยอม ข้อเท็จจริงการเปิดเผย และตัวบทฉบับที่มีผลใช้บังคับกับ
[เอกสารทางการ](https://www.creditinfocommittee.or.th/api/file/pdf/law_act/Credit%20Info%20Act%20update%201-6.pdf)

## สรุปว่า mode ใดดีที่สุด

**สำหรับ OpenThai 2.0 Legal ถ้าเป้าหมายคือคำตอบกฎหมายที่ต้องอ้างชื่อกฎหมาย
และเลขมาตราแม่นยำ `Citation RAG` แบบ focused evidence ให้ผลดีที่สุดใน
การทดสอบนี้** แต่คำว่า RAG ในที่นี้หมายถึง pipeline ที่ค้นให้ครอบคลุม
แล้วลด context ให้เหลือเฉพาะมาตราที่ใช้จริง ไม่ใช่ส่ง top-k จำนวนมากให้
โมเดลเลือกเองทั้งหมด

| ลำดับแนะนำ | Mode | ผลที่พบ | เหมาะกับงาน | ข้อจำกัด/ระดับตรวจทาน |
|---:|---|---|---|---|
| 1 | **Citation RAG — focused evidence** | NCB 5/5; open-book echo 9/9 | ถามข้อกฎหมาย, ระบุมาตรา, compliance checklist ที่ต้องมี citation | ดีที่สุดในชุดนี้ แต่ต้องตรวจ retrieval, ฉบับกฎหมาย และคำอธิบายโดยมนุษย์ |
| 2 | **Legal essay — thinking off + RAG** | พบ citation anchors ครบ 2/2; เฉลี่ย 41.68 วินาที | ร่างบทวิเคราะห์, legal memo, IT audit finding เมื่อมีตัวบท/มาตราประกอบ | เขียนเป็นระบบได้ แต่ยังอธิบายบทบาทมาตราหรือขั้นตอนคดีคลาดเคลื่อนได้ |
| 3 | **General legal chat + RAG** | สนทนาต่อเนื่องผ่าน 3/3 turns; เฉลี่ย 24.73 วินาที | อธิบายกฎหมายภาษาทั่วไป, เก็บ requirement, ร่างคำถามหรือ checklist | จำบริบทได้ แต่ paraphrase กฎหมายกว้างเกิน evidence ได้ ไม่ควรใช้เป็น legal opinion |
| 4 | **Legal essay — thinking on** | 1 case อ้างครบ, 1 case recall 50%; เฉลี่ย 109.35 วินาที | งานทดลองที่ต้องการ reasoning ยาวและมีเวลาตรวจ output | รอบนี้ช้ากว่า thinking off 2.62 เท่า มี reasoning ภาษาอังกฤษปน และไม่ช่วยคุณภาพสม่ำเสมอ |
| 5 | **Closed-book** | strict 0/5 ในชุดควบคุม | brainstorming, จัดหมวดคำถาม หรือหา keyword เพื่อเริ่มค้น | ไม่เหมาะกับการยืนยันเลขมาตรา; อาจตอบอย่างมั่นใจทั้งที่มาตราผิดและไม่ abstain |

หมายเหตุ: NCB thinking-on case ใช้ evidence packet รุ่นก่อน optimize จึงไม่ควร
ตีความ citation recall 50% ว่าเกิดจาก thinking เพียงปัจจัยเดียว ส่วนเวลาที่
ช้าขึ้นและ reasoning ภาษาอังกฤษปนเป็นสิ่งที่สังเกตได้โดยตรงจาก serving
stack รอบนี้

### เหตุใด RAG จึงยังไม่ถูกทุกกรณี

- ถ้าส่งเฉพาะมาตราที่ถูกต้อง โมเดลได้ citation 9/9
- ถ้าส่ง 10 มาตราที่มี hard negatives ปนกัน ผล exact citation เหลือ 5/9
- NitiBench retrieval แบบ legal advanced ที่ `k=20` มี hit rate 92.17%
  แต่ retrieval hit ไม่ได้แปลว่า generator จะเลือกมาตรานั้นถูก
- หลังใช้ candidate 32 → OpenThai rerank → cross-reference expansion →
  focused evidence 2–6 chunks ชุด NCB จึงได้ 5/5

ดังนั้นข้อสรุปคือ **RAG เป็น mode ที่แนะนำที่สุด แต่คุณภาพขึ้นกับการเตรียม
structural chunks, retrieval, rerank, evidence ordering และ citation
validation ทั้งระบบ**

### เลือก mode ตามงาน

| ความต้องการ | Mode ที่ควรเริ่ม |
|---|---|
| ต้องการคำตอบพร้อมชื่อกฎหมาย/มาตรา | Citation RAG |
| มีข้อเท็จจริงและต้องร่างบทวิเคราะห์ยาว | Legal essay thinking off + RAG |
| ต้องการคุยต่อเนื่องหรือแปลงกฎหมายเป็น checklist | General legal chat + RAG |
| ยังไม่มีคลังเอกสารและต้องการเพียง keyword สำหรับค้นต่อ | Closed-book แล้วนำผลไปค้น primary source ห้ามใช้เป็นข้อสรุป |
| ต้องการทดลอง reasoning ยาว | Legal essay thinking on แยกเป็น experiment |

ค่าพารามิเตอร์ที่ใช้ตามคำแนะนำของ model card:

| Mode | temperature | top_p | max_tokens | thinking |
|---|---:|---:|---:|---|
| Citation RAG / closed-book control | 0.0 | 1.0 | 2,048 | off |
| Legal essay | 0.7 | 0.9 | 4,096 | off |
| Legal essay thinking | 0.7 | 0.9 | 6,144 | on |
| General legal chat | 0.7 | 0.9 | 2,048 | off |

## รายงาน

| รายงาน | สรุป |
|---|---|
| [OpenThai vs Qwen3.6-27B controlled comparison](reports/qwen27-controlled-comparison-20260729/) | ใช้ evidence packet เดียวกันเทียบ Echo, Selection, NCB, Closed-book, Essay และ legal chat; แยก JSON failure, citation และ legal substance |
| [Advanced hybrid RAG + Codex judge](reports/advanced-hybrid-rag-20260729/) | BM25/FTS5/Dense/Hybrid, OpenThai rerank, Qdrant/Chroma/Milvus, NitiBench 115 retrieval questions, generation ทุก mode และ failure analysis |
| [NCB structural chunks: NitiBench format, OpenThai vs Qwen](reports/ncb-nitibench-qwen-comparison-20260729/) | 6 หมวดคำถามข้อมูลเครดิต × Echo/Selection/RAG, ผล 36 คำตอบ, ตรวจ format ก่อน/หลัง และ Codex judgement ที่ตรวจย้อนกลับได้ |
| [NitiBench + Ground Truth RAG](reports/nitibench-ground-truth-20260729/) | สรุปเข้าใจง่าย, ตรวจความสอดคล้องกับ model card/คู่มือ RAG/API, ผล retrieval และ 4 modes |
| [Three generation profiles](reports/OPENTHAI_THREE_GENERATION_PROFILES_FULL_OUTPUT_20260729.md) | ผลเต็มของ Legal essay และ General chat หลาย profile |
| [Dummy-news context-to-law evaluation](reports/DUMMY_NEWS_CONTEXT_TO_LAW_USECASE_20260729.md) | การจำแนกบริบทข่าวไปสู่กฎหมายที่เกี่ยวข้อง |
| [SEC false-report use case](reports/SEC_BITKUB_FALSE_REPORT_USECASE_20260729.md) | เปรียบเทียบ Open-book, Closed-book และ Legal essay |

## ขอบเขตและการใช้อย่างรับผิดชอบ

- ไม่เก็บ model weights, token, database credential หรือ chat sessions ใน repository
- เอกสาร/ข่าวที่ใช้สร้าง scenario ไม่ได้ถือเป็นตัวบทปฐมภูมิ
- การทดสอบไม่ใช่ official benchmark ของ OpenThai และไม่มีการใช้ Claude หรือ LLM judge เว้นแต่รายงานนั้นระบุเป็นอย่างอื่น
- สำหรับ production RAG ให้ใช้ตัวบทที่ตรวจสอบได้, เก็บ page/section provenance, บังคับ structured citations และให้ผู้มีวิชาชีพกฎหมายตรวจทาน
