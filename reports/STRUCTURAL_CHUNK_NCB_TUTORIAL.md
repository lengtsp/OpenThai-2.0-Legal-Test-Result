# วิธีทำ Structural Chunk สำหรับ พ.ร.บ. ข้อมูลเครดิต (NCB RAG)

## เป้าหมาย

การทำ RAG กฎหมายไม่ควรเริ่มจาก “ตัดทุก 1,000 ตัวอักษร” แต่ควรให้หน่วย retrieval ตรงกับหน่วยที่กฎหมายใช้อ้างอิง:

```text
เอกสาร
└── หมวด
    └── มาตรา
        ├── วรรค
        └── อนุมาตรา
```

สำหรับ PDF นี้ หนึ่ง `มาตรา` เป็น retrieval unit หลัก หากยาวเกิน context จึงค่อยแบ่งเป็น part โดยคง `section_id` เดิม

## ผลจากเอกสารจริง

- PDF ทางการ: 24 หน้า
- SHA-256: `324e4087ea90bcb1467ebc379bd665e902ecc142737c60e102ea5425df0f732a`
- Final database ingest: `500a1f7b-0019-408b-98dc-cf989b8888ff`
- โครงสร้างทั้งหมดรวมภาคผนวก: 79 sections / 81 chunks
- ชุดกฎหมายฉบับรวมปัจจุบันสำหรับ Open WebUI: 73 sections / 74 chunks
- Embedding: `Qwen3-Embedding-4B`, 2,560 dimensions
- Page anchor: ครบทุก chunk

ภาคผนวกหน้าที่ 22–24 เป็นข้อความจากพระราชบัญญัติฉบับแก้ไขซึ่งมีเลขมาตราซ้ำกับกฎหมายหลัก จึงเก็บไว้ในฐานเพื่อ audit แต่ไม่นำไปรวมกับ Knowledge base ฉบับปัจจุบัน

## ปัญหาที่พบจาก plain text

### 1. เลขเชิงอรรถติดเลขมาตรา

PDF แสดงหัวข้อ `มาตรา ๒` แล้วมีเชิงอรรถ `๑` อยู่ข้างบน แต่ plain text กลายเป็น:

```text
มาตรา ๒๑ พระราชบัญญัตินี้ให้ใช้บังคับ...
```

กรณีมาตราที่มีเครื่องหมาย `/`:

```text
มาตรา ๒๔/๑๑๙ ...
```

ความหมายที่ถูกคือ `มาตรา ๒๔/๑` + เชิงอรรถ `๑๙` ไม่ใช่มาตรา `24/119`

วิธีแก้:

1. อ่านเลขตามลำดับมาตราก่อนหน้า
2. แยก base section และ slash section
3. เก็บเลข canonical เป็น Arabic string เช่น `24/1`
4. แทนหัวข้อใน content ด้วย `มาตรา ๒๔/๑`

### 2. เชิงอรรถท้ายหน้าปนในเนื้อหามาตรา

PyMuPDF plain text จะต่อประวัติแก้ไขกฎหมายท้ายหน้าเข้ากับมาตราที่กำลังอ่าน เช่น มาตรา 26 ถูกต่อด้วยเชิงอรรถ 23 และ 24

วิธีแก้คืออ่าน `page.get_text("dict")` เป็น layout blocks แล้วตัด block ที่:

- เริ่มต่ำกว่า 70% ของความสูงหน้า; และ
- ขึ้นต้นด้วยเลขเชิงอรรถ ตามด้วย `มาตรา` หรือ `หมวด`

ไม่ควรลบด้วย keyword ทั่วทั้งเอกสาร เพราะอาจลบ cross-reference ที่เป็นเนื้อหากฎหมายจริง

### 3. Cross-reference ถูกเข้าใจว่าเป็นหัวมาตราใหม่

ข้อความต่อหน้าบางหน้าเริ่มด้วย:

```text
มาตรา ๒๐/๑ วรรคสาม ต้องระวางโทษ...
```

แต่เป็นการอ้างถึงมาตรา 20/1 ภายในมาตราโทษ ไม่ใช่หัว chunk ใหม่ วิธีแยกคือใช้ลำดับมาตรา: ถ้าขณะอ่านมาตรา 50 แล้วพบเลข 20/1 ที่ต้นบรรทัด ให้ถือเป็นเนื้อหาต่อเนื่อง ไม่เปิด chunk ใหม่

### 4. ภาคผนวกมีเลขมาตราซ้ำ

ฉบับแก้ไขแต่ละฉบับมี `มาตรา ๒` ของตนเอง หาก export ด้วยชื่อ `section-2.md` จะทับมาตรา 2 ของกฎหมายหลัก จึงต้องแยก:

```text
active-law corpus: หน้า 1–21
historical amendment corpus: หน้า 22–24
```

## ขั้นตอนสร้าง chunk

### 1. สร้าง source manifest

เก็บอย่างน้อย:

```json
{
  "source_filename": "credit_info_act_update_1_6.pdf",
  "source_file_hash": "324e4087...",
  "source_url": "https://www.creditinfocommittee.or.th/...",
  "page_count": 24,
  "extraction_method": "PyMuPDF layout blocks",
  "build_timestamp": "ISO-8601"
}
```

Hash ช่วยยืนยันว่าการ re-index และ benchmark ใช้เอกสารฉบับเดียวกัน

### 2. อ่าน layout block และกรอง footnote

```python
blocks = sorted(
    (b for b in page.get_text("dict")["blocks"] if "lines" in b),
    key=lambda b: (b["bbox"][1], b["bbox"][0]),
)

is_footnote = (
    block["bbox"][1] >= page.rect.height * 0.70
    and re.match(r"^[๐-๙0-9]+\s+(มาตรา|หมวด)", block_text)
)
```

ควร render/ตรวจหน้าที่มีเชิงอรรถหลายรายการก่อนเลือกค่า `0.70`

### 3. ติดตาม state ของหมวดและมาตรา

```python
current_topic = "บททั่วไปและคำนิยาม"
current_section = None

if line.startswith("หมวด"):
    current_topic = chapter_heading
elif line.startswith("มาตรา"):
    close_previous_section()
    current_section = new_section()
else:
    current_section.lines.append(line)
```

เมื่อ section ต่อข้ามหน้า ให้เปลี่ยน `page_end` แต่ห้ามเปิด chunk ใหม่

### 4. สร้าง metadata

ตัวอย่างมาตรา 17:

```json
{
  "law_name": "พระราชบัญญัติการประกอบธุรกิจข้อมูลเครดิต พ.ศ. ๒๕๔๕ (รวมฉบับแก้ไข ๑-๖)",
  "section_id": "17",
  "section_heading": "มาตรา ๑๗",
  "topic": "หมวด ๓ สิทธิและหน้าที่ของบริษัทข้อมูลเครดิต สมาชิกและผู้ใช้บริการ",
  "page_start": 6,
  "page_end": 6,
  "structural_path": [
    "พระราชบัญญัติการประกอบธุรกิจข้อมูลเครดิต...",
    "หมวด ๓...",
    "มาตรา ๑๗"
  ],
  "part": 1,
  "parts": 1,
  "content_sha256": "..."
}
```

ข้อสำคัญคือ answer citation ใช้ `section_id: "17"` ขณะที่ UI แสดง `มาตรา ๑๗` และหน้า 6

### 5. แบ่งเฉพาะมาตราที่ใหญ่จริง

กำหนด `max_chars=4000` ใน corpus นี้เพื่อรักษาหนึ่งมาตราต่อหนึ่ง chunk ให้มากที่สุด หากต้องแบ่ง:

```text
มาตรา 20 / part 1 of 2
มาตรา 20 / part 2 of 2
```

ทั้งสอง part ต้องมี `section_id=20` เหมือนกัน และ retriever ต้อง deduplicate/reassemble ก่อนส่งให้โมเดล

## ตัวอย่าง Good Chunk: มาตรา 17

คำถาม:

> IT Internal Audit ควรตรวจหลักฐานใดเกี่ยวกับการเข้าถึงข้อมูล NCB และต้องเก็บ log นานเท่าใด

มาตรา 17 เป็น chunk ที่เหมาะ เพราะมี requirement ครบในหน่วยเดียว:

- ระบบรักษาความลับและความปลอดภัย
- ป้องกันผู้ไม่มีสิทธิ
- ป้องกันการแก้ไข/ทำลายโดยไม่ได้รับอนุญาต
- บันทึกและรายงานทุกครั้งเมื่อเข้าถึง
- เก็บบันทึกไม่น้อยกว่าสองปี

retrieval packet ที่ส่งให้โมเดลควรมีรูปแบบ:

```text
[law_name: พระราชบัญญัติการประกอบธุรกิจข้อมูลเครดิต...;
 section: 17; PDF page: 6]
มาตรา ๑๗ ...ข้อความครบทั้งมาตรา...
```

ไม่ควรส่งมาตรา 20, 30 หรือ 39 เพียงเพราะมีคำว่า “ข้อมูล” หรือ “ตรวจสอบ” เหมือนกัน

## Pipeline ที่แนะนำ

```text
User question
  → BM25 candidate top 10
  → Qwen embedding candidate top 10
  → union + deduplicate by (law_name, section_id)
  → multilingual reranker
  → retain 1–3 complete sections
  → OpenThai JSON citation answer
  → citation/evidence validator
```

ผล benchmark ก่อนปรับ Open WebUI:

| Mode | Relevant precision | Relevant recall |
|---|---:|---:|
| ส่งมาตราที่ถูกต้องครบ | 100% | 100% |
| มาตราถูก + distractors | 70.0% | 86.7% |
| Dense embedding top-4 | 40.0% | 66.7% |

จุดที่ทำให้คำตอบดีขึ้นจึงไม่ใช่การเพิ่ม `top_k` อย่างเดียว แต่คือการทำ structure, hybrid retrieval, rerank และส่งเฉพาะมาตราที่เกี่ยวข้อง

## Quality gates

ก่อน embedding ต้องผ่าน:

- active section id ไม่ซ้ำ
- content ไม่ว่างและเริ่มด้วย canonical heading
- ทุก chunk มี `page_start/page_end`
- ไม่มี footnote-only chunk
- ไม่มีเชิงอรรถแก้ไขกฎหมายปนใน body
- ไม่มี descending cross-reference ถูกสร้างเป็นหัวมาตรา
- inspect ด้วยมืออย่างน้อย 6 กรณี: แรก, สุดท้าย, ยาวที่สุด, ข้ามหน้า, slash section และ footnote-heavy

## ใช้ Skill ที่สร้างไว้

Skill ที่ติดตั้ง:

```text
$extract-structural-legal-chunks
```

ตัวอย่างคำสั่ง:

```text
Use $extract-structural-legal-chunks to extract this Thai regulatory PDF
into page-anchored section chunks and prepare an Open WebUI package.
```

ตัวสคริปต์ทั่วไปของ skill รองรับ `--page-end 21` เพื่อแยก active law ออกจากภาคผนวกและสร้าง `manifest.json`, `chunks.jsonl`, `quality.json` และไฟล์ Markdown สำหรับ Open WebUI
