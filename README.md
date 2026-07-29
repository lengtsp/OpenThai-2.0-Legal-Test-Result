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

- **RAG สำคัญกว่าการพึ่ง Closed-book**: เมื่อมีตัวบทที่ถูกต้อง โมเดลตอบตาม evidence ได้ดีขึ้น; เมื่อไม่มี context อาจอ้างมาตราผิดหรือไม่ครบ
- **Chunk ต้องแบ่งตามมาตรา**: `law_name` + `section` และข้อความของมาตราเป็นรูปแบบที่ตรงกับคำแนะนำผู้พัฒนาและเอื้อต่อการตรวจ citation
- **Selection เป็นจุดเสี่ยง**: มีหลักฐานหลายมาตราที่คล้ายกันแล้วโมเดลยังเลือกเกิน/ตกหล่นได้ จึงต้องมี retriever ที่ดี, output validator และ human review
- **NCB RAG ต้องแก้ retrieval ก่อนเลือกโมเดล**: ใน 6 หมวดข้อมูลเครดิต Qwen ได้คะแนนตรวจเนื้อคำตอบโดย Codex สูงกว่าในรอบนี้ (2.44/3 เทียบ 2.06/3) แต่ทั้งสองพลาดกรณีพนักงานทำข้อมูลรั่วไหลเมื่อ top-5 ไม่ดึงมาตรา 24 และ 54 ขึ้นมา
- **อย่าดูคะแนนรวมเพียงค่าเดียว**: ผล retrieval แตกต่างมากตามกลุ่มกฎหมาย จึงรายงานแยก CCL, Tax และ scenario สำคัญ

ผลทั้งหมดเป็น **decision-support evaluation ไม่ใช่คำแนะนำกฎหมาย** และทุกมาตราต้องตรวจเทียบตัวบทฉบับปัจจุบันก่อนใช้งานจริง

## รายงาน

| รายงาน | สรุป |
|---|---|
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
