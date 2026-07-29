# NCB structural chunks — NitiBench format, OpenThai vs Qwen 27B

ผลนี้เป็นการทดสอบอิสระเพื่อปรับคลัง RAG ของ **พระราชบัญญัติการประกอบธุรกิจข้อมูลเครดิต** (NCB/Credit Bureau Act) ไม่ใช่คำวินิจฉัยกฎหมาย และผู้จัดทำไม่ใช่ผู้พัฒนา OpenThai หรือ Qwen

## สรุปที่อ่านง่าย

ทดสอบ 6 หมวดคำถามที่ตรงกับคลัง NCB โดยแต่ละหมวดมี 3 แบบ: ให้ตัวบทที่ถูกต้องพอดี (Echo), ผสมมาตราที่ไม่เกี่ยว (Selection) และค้นคืนจริงจาก 73 มาตรา (RAG top-5) รวม **36 คำตอบ** จาก 2 โมเดล

| หมวดคำถาม | มาตราหลักที่คาดหวัง | RAG ได้หลักฐานครบใน top-5 หรือไม่ | ข้อสังเกตที่สำคัญ |
|---|---:|---:|---|
| Consent สำหรับ annual review | 20 | ได้ | Qwen อ้างเฉพาะมาตรา 20; OpenThai เพิ่มมาตรา 28 ที่ไม่เกี่ยว |
| ส่งข้อมูลไปทำ cross-selling | 20, 22 | ไม่ครบ (ขาด 22) | ทั้งสองโมเดลไม่ควรตัดสินจาก RAG ชุดนี้โดยลำพัง |
| ปฏิเสธสินเชื่อจากเครดิตบูโร | 28 | ได้ | ทั้งคู่ตอบสาระสำคัญได้ |
| ข้อมูลค้างชำระผิด/ขอแก้ไข | 19, 26 | ได้ | Qwen อธิบายถูกเป็นหลัก แต่ cite ไม่ครบมาตรา 19 |
| พนักงานทำข้อมูลเครดิตรั่วไหล | 24, 54 | ไม่ได้ | เป็น failure ของ retrieval; คำตอบ RAG จึงอ้างฐาน/โทษไม่ตรง |
| สร้าง credit model | 20/1 | ได้ | Qwen เก็บเงื่อนไข “ไม่ระบุตัวบุคคล + consent + วัตถุประสงค์” ได้ครบกว่า |

**ข้อสรุป:** การแปลงเป็น schema ที่เข้ากับ NitiBench ทำให้ตรวจสอบข้อมูลและเชื่อมต่อระบบได้เป็นระเบียบขึ้น แต่ไม่ได้แก้ retrieval ทุกกรณี ชุดข้อมูลนี้ยังต้องเพิ่ม hybrid search/reranking และ rule สำหรับจับคู่ “ฐานความลับ + บทกำหนดโทษ” ก่อนนำไปใช้กับงานธนาคารจริง

## ผลเชิงตัวเลข

Citation precision/recall เทียบกับชุดมาตราที่กำหนดไว้ล่วงหน้า; ค่าเฉลี่ยเป็น macro-average ต่อ 6 สถานการณ์

| โมเดล | Mode | JSON ถูกต้อง | Citation P/R | เวลาเฉลี่ย/คำตอบ |
|---|---|---:|---:|---:|
| OpenThai 2.0 Legal | Echo | 6/6 | 1.000 / 1.000 | 16.66 s |
| OpenThai 2.0 Legal | Selection | 6/6 | 0.889 / 1.000 | 19.20 s |
| OpenThai 2.0 Legal | RAG top-5 | 6/6 | 0.417 / 0.667 | 17.06 s |
| Qwen3.6-27B | Echo | 6/6 | 1.000 / 0.917 | 10.81 s |
| Qwen3.6-27B | Selection | 6/6 | 0.861 / 0.917 | 5.77 s |
| Qwen3.6-27B | RAG top-5 | 6/6 | 0.667 / 0.583 | 9.26 s |

Codex ตรวจเนื้อคำตอบตาม rubric โปร่งใสได้ **37/54 (2.06/3)** สำหรับ OpenThai และ **44/54 (2.44/3)** สำหรับ Qwen รายข้อและเหตุผลอยู่ใน [Codex judgement](codex-judgement.md) และคำตอบเต็มทุกข้ออยู่ใน [raw review packet](raw-review-packet.md)

## การเทสนี้ตอบเรื่อง format หรือไม่

ตอบได้ในระดับหนึ่ง: corpus เดิมมีหนึ่งมาตราต่อหนึ่งไฟล์อยู่แล้ว จึงมีแนวคิดใกล้กับ NitiBench แต่ข้อมูลอยู่ใน `<law ...>` สำหรับ Open WebUI และ provenance แยกใน manifest ไม่ใช่ record schema โดยตรง รอบนี้แปลงเป็น

```json
{
  "law_name": "...",
  "section_num": "20",
  "section_content": "... มาตรา ๒๐ ...",
  "metadata": {"page_start": 7, "page_end": 8, "topic": "..."}
}
```

มี 73 records, ไม่มี section ซ้ำ, ทุก record มี page provenance และ hash, และตัดประกาศ/หมายเหตุที่ปนท้ายมาตรา 66 ออก การเทียบ dense retrieval ก่อน/หลังพบ Recall@5 เพิ่มจาก **0.667 เป็น 0.750** ในเพียง 6 queries แต่ผลขึ้นลงรายข้อ (ดีขึ้นที่ consent, แย่ลงที่ cross-selling) จึงยังสรุปไม่ได้ว่า “schema ใหม่ทำให้ค้นหาแม่นกว่า” อย่างมีนัยสำคัญ ดูรายละเอียดใน [methodology and format comparison](methodology.md)

## Parameter ที่ใช้

ใช้ citation-answering profile เดียวกันกับทั้งสองโมเดล: `temperature=0.0`, `top_p=1.0`, `max_tokens=2048`, `thinking=off`, `seed=42` และบังคับ JSON citation จากเฉพาะ context ที่ให้

- OpenThai 2.0 Legal รันผ่าน vLLM บน `127.0.0.1:3033` (context 32k)
- Qwen3.6-27B รันผ่าน llama.cpp บน `127.0.0.1:8081` (context 12,032)
- embedding/retrieval ใช้ Qwen3-Embedding-4B เดียวกันกับทั้งสองฝั่ง

ข้อความหลักฐานใน top-5 สั้นกว่าขีด context มาก จึงไม่ใช่การทดสอบ long-context; ความแตกต่างที่เห็นส่วนใหญ่เป็น retrieval/citation behaviour

## คำถามนอกขอบเขตของคลัง NCB

หมวดด้านล่างเป็นตัวอย่างคำถามที่หน้าเว็บควร route ไปยังคลังกฎหมายอื่น ไม่ควรนำผลชุดนี้ไปอ้างว่า NCB รองรับ

| ประเภทคำถามง่าย | คลังกฎหมายที่ควรคัดเลือกก่อนตอบ |
|---|---|
| ลักทรัพย์/ขโมยของ, ชนคน, พนันออนไลน์ | ประมวลกฎหมายอาญา และกฎหมายเฉพาะที่เกี่ยวข้อง |
| ข้อมูลรั่วไหลทั่วไป | PDPA, กฎหมายความมั่นคงปลอดภัยไซเบอร์ และนโยบายองค์กร |
| โดนไล่ออก | กฎหมายคุ้มครองแรงงาน/สัญญาจ้าง |
| ค้างค่าบัตรเครดิต, ปล่อยกู้นอกระบบ | กฎหมายแพ่งและพาณิชย์, ดอกเบี้ย/ทวงถามหนี้ และกฎหมายสินเชื่อที่เกี่ยวข้อง |
| สร้างอาคาร, เปิดร้าน | กฎหมายควบคุมอาคาร ใบอนุญาต และข้อบัญญัติท้องถิ่น |
| ขับรถไม่มีใบขับขี่ | กฎหมายจราจรทางบกและกฎหมายที่เกี่ยวข้อง |

การทดสอบเพิ่มสำหรับแต่ละคลังต้องมีตัวบทปฐมภูมิและ ground truth แยก ไม่ใช่ reuse ชุด NCB นี้

## เอกสารและผลเต็ม

- [Methodology + before/after format comparison](methodology.md)
- [Codex judgement](codex-judgement.md)
- [Raw answers: 36 outputs](raw-review-packet.md)
- [Raw model results JSON](raw-results/)
- [Quality manifest for the NitiBench-compatible corpus](corpus-quality.json)

อ้างอิงแนวทางของผู้พัฒนา: [model card](https://huggingface.co/iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b), [RAG tutorial](https://iapp.co.th/openmodels/openthai2p0-legal-rag-tutorial), และ [NitiBench dataset](https://huggingface.co/datasets/VISAI-AI/nitibench)
