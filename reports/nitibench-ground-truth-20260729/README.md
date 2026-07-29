# NitiBench + Ground Truth RAG — สรุปสำหรับผู้อ่านทั่วไป

## ทดสอบเรื่องอะไร

รายงานนี้เป็นการทดสอบอิสระของ
[`OpenThai 2.0 Legal`](https://huggingface.co/iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b)
ผ่าน vLLM บนเครื่อง local ไม่ใช่ผลรับรองจากผู้พัฒนา และไม่ใช่คำแนะนำกฎหมาย

เป้าหมายคือดูว่าเมื่อใช้โมเดลกับกฎหมายไทย จะเกิดอะไรขึ้นใน 4 รูปแบบงานจริง:

| รูปแบบ | สิ่งที่ทดสอบ | สิ่งที่เกิดขึ้นในรอบนี้ |
|---|---|---|
| RAG — Echo | ให้เฉพาะมาตราที่ถูกต้อง แล้วให้ตอบตามหลักฐาน | กรณีตัวอย่างมาตรา 302/1 ตอบและอ้างหลักฐานที่ให้ได้ |
| RAG — Selection | ให้มาตราที่เกี่ยวข้องปนมาตราใกล้เคียง แล้วเลือกเฉพาะที่ใช้ | มีข้อผิดพลาด: เลือกมาตรา 326 ทั้งที่โจทย์ตัดประเด็นหมิ่นประมาทบุคคลออก และตกหล่น 14(5) |
| Closed-book | ไม่ให้ตัวบทเลย ให้ตอบจากความจำของโมเดล | คำตอบยาวจนถูกตัดที่ 1,536 tokens และอ้างมาตราไม่ตรงกับ ground truth ของโจทย์ |
| Legal essay | ให้เขียนบันทึก/วิเคราะห์เป็นภาษาไทย | จัดโครงข้อเท็จจริงและ evidence gap ได้ดี แต่ไม่ใส่รูปแบบ citation `[n]` ที่สั่ง |

นอกจากนี้วัดการค้นคืน (retrieval) ของ NitiBench เพื่อแยกให้ชัดว่า
“ค้นเอกสารถูกหรือไม่” ออกจาก “โมเดลตีความและอ้างอิงถูกหรือไม่”

## ผลสรุปสั้น ๆ

1. **ใช้ RAG เป็นค่าเริ่มต้นสำหรับงานกฎหมาย** ผล Closed-book รอบนี้ยืนยันว่าการตอบจากความจำเพียงอย่างเดียวไม่พอสำหรับงานที่ต้องอ้างมาตราเฉพาะ
2. **คุณภาพการค้นคืนมีผลโดยตรงต่อคำตอบ**: NitiBench Recall@5 อยู่ที่ **85.90%** แต่ CCL 88.75% และ Tax 58.00% จึงไม่ควรนำคะแนนรวมไปสรุปว่าใช้ได้ดีเท่ากันทุกกฎหมาย
3. **การเลือกท่ามกลางมาตราใกล้เคียงเป็นจุดเสี่ยง**: แม้ให้ evidence แล้ว โมเดลยังเลือกมาตราเกิน/ตกหล่นได้ จึงต้องมี citation validator และผู้ตรวจทานสำหรับงานสำคัญ
4. **Legal essay ใช้ช่วยร่างได้ แต่ไม่ควรเป็นตัวตัดสิน**: ต้องตรวจข้อความอ้างอิงกับตัวบทปัจจุบันก่อนใช้งาน

## แนวทางทดสอบสอดคล้องกับต้นฉบับหรือไม่

**คำตอบ: สอดคล้องในแกนหลัก แต่ยังไม่ครบตามเส้นทางที่โมเดลถูกปรับให้ทำได้ดีที่สุด**

| หัวข้อจากผู้พัฒนา | สถานะของรอบทดสอบ | ความหมาย |
|---|---|---|
| แยก Open-book echo, selection, closed-book และ legal essay | **สอดคล้อง** | เป็น 4 โหมดเดียวกับ model card |
| ใช้ NitiBench วัด RAG | **สอดคล้อง** | RAG tutorial แนะนำ NitiBench สำหรับวัด pipeline end-to-end |
| แบ่งกฎหมายหนึ่งมาตราต่อหนึ่ง chunk พร้อม `law_name` + `section` | **สอดคล้อง** | เป็นรูปแบบ chunk ที่ RAG tutorial ระบุ |
| self-host ผ่าน vLLM, context 32,768 | **สอดคล้อง** | อยู่ในรูปแบบ serving ที่ model card ระบุว่ารองรับ |
| ใช้ Qwen3-Embedding-4B | **ยอมรับได้ แต่ไม่ใช่การจำลอง hosted API** | model card ระบุว่าใช้ retriever ใดก็ได้; hosted API ใช้ hybrid BM25 + embedding + reranker คนละชุด |
| ใช้ JSON citation contract ที่โมเดลฝึก/RL มา | **ยังไม่สอดคล้อง** | รอบนี้ใช้คำตอบ prose พร้อม `[n]` จึงไม่ใช่การวัดเส้นทาง citation ที่แข็งแรงที่สุดของโมเดล |
| Citation/closed-book `max_tokens=2048`, essay `4096` | **ยังไม่ครบ** | รอบ diagnostic ใช้ 1,536 และ 2,048 ตามลำดับเพื่อควบคุมเวลา; อยู่เหนือขั้นต่ำ citation แต่ต่ำกว่าคำแนะนำเต็มสำหรับ essay |
| ตัวบทกฎหมายปัจจุบันเป็น corpus หลัก | **ยังไม่สอดคล้องสำหรับ production** | NitiBench ถูกใช้เป็น corpus ทดสอบแบบควบคุม; ตัวอย่าง ground truth มาจากข่าวและเป็น source-reported evidence ไม่ใช่ตัวบทปฐมภูมิ |

ดังนั้น ผลนี้เหมาะจะเรียกว่า **diagnostic benchmark ที่ออกแบบถูกทิศทาง**:
ใช้หาจุดแข็ง/จุดเสี่ยงของ RAG และโมเดลได้ แต่ยังไม่ใช่ผลรับรองว่า pipeline พร้อมใช้กับกฎหมายปัจจุบันจริง

### หมายเหตุเรื่อง generation settings

เอกสารต้นฉบับแยก configuration ตามงาน: model card แนะนำ citation ที่
`temperature=0`, `top_p=1`, `max_tokens=2048` และ legal essay ที่
`temperature=0.7`, `top_p=0.9`, `max_tokens=4096` (6,144 เมื่อเปิด thinking)
ส่วน API guide แนะนำให้ legal essay ที่ใช้ RAG ตั้ง `rag_inject="system"` และ
เปิด thinking พร้อม `temperature=0`; citation JSON ใช้ `rag_inject="user"`.
จึงไม่ควรอ้างผลรอบนี้ว่าเป็น “ค่า parameter ที่ดีที่สุด” เพราะรอบนี้ยังไม่ได้
ทดสอบสอง profile ตามคู่มือให้ครบทั้งชุด

## ควรทำอะไรต่อก่อนใช้จริง

1. สร้าง corpus จากตัวบทปัจจุบันที่ตรวจสอบได้ แล้วแบ่งหนึ่ง `มาตรา` ต่อหนึ่ง chunk พร้อมชื่อกฎหมายและเลขมาตรา
2. เปลี่ยน citation mode เป็น JSON contract ตามตัวอย่างใน model card แล้วตรวจ JSON, `law_name`, `section` และการอ้างเกิน context โดยโปรแกรม
3. ทดสอบ Echo และ Selection แยกกัน: Echo วัดว่าโมเดลอ่านมาตราที่ถูกต้องได้หรือไม่; Selection วัด retriever + การคัดมาตราใกล้เคียง
4. ใช้ค่าที่ผู้พัฒนาแนะนำจริงในการวัดรอบถัดไป และแยกสอง profile: citation JSON (`rag_inject="user"`) และ RAG legal essay (`rag_inject="system"` + thinking)
5. ประเมินแยกตามกลุ่มกฎหมาย โดยเฉพาะ Tax ที่ retrieval รอบนี้อ่อนกว่า CCL มาก และมีผู้เชี่ยวชาญตรวจคำตอบความเสี่ยงสูง

## เอกสารประกอบ

- [ผลดิบ ตาราง metric และคำตอบจริง](raw-results.md)
- [Model card และ 4 evaluation modes](https://huggingface.co/iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b)
- [คู่มือสร้าง RAG / Open WebUI / OpenThaiRAG](https://iapp.co.th/openmodels/openthai2p0-legal-rag-tutorial)
- [API documentation และ RAG parameters](https://iapp.co.th/docs/llm/openthai2p0-legal)

ไม่มีการใช้ Claude หรือ LLM judge ในรอบนี้; ตัวเลขผลลัพธ์มาจาก raw model output และการตรวจแบบ deterministic เท่านั้น.
