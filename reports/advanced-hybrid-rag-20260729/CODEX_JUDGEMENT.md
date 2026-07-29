# Codex Judgement

การประเมินนี้อ่านคำตอบเต็มจาก `opengpt_modes.json` และ
`nitibench_generation_selection.json` หลังคำนวณ citation metrics แล้ว
Codex ไม่ได้ใช้ Claude และไม่ได้แก้ ground truth หลังเห็นคำตอบ

ระดับผล:

- **ผ่าน** — citation และสาระสำคัญตรงหลักฐานในขอบเขตที่ตรวจ
- **ผ่านแบบมีเงื่อนไข** — ใช้ช่วยร่างได้ แต่มีข้อความกว้าง/ต้องตรวจต่อ
- **ไม่ผ่าน** — ผิดมาตราสำคัญ, ไม่ abstain หรืออธิบายเกินหลักฐานอย่างมีนัยสำคัญ

## Citation RAG — NCB

| Scenario | Verdict | เหตุผล |
|---|---|---|
| พนักงานส่งรายงานเครดิตเข้า Line | ผ่านในมิติ citation | อ้างมาตรา 24 และบทลงโทษมาตรา 54 ตรง evidence |
| Cross-selling บริษัทประกันในเครือ | ผ่านในมิติ citation | อ้างมาตรา 20 และ 22 ครบและไม่เพิ่มมาตรา |
| ใบอนุญาต/สิทธิประกอบธุรกิจ | ผ่านในมิติ citation | อ้างมาตรา 6 และ 9 ครบ |
| ปฏิเสธสินเชื่อ/โต้แย้ง | ผ่านในมิติ citation | อ้างมาตรา 26, 27, 28 ครบ |
| วงจรข้อมูลสามเหตุการณ์ | ผ่านในมิติ citation | อ้างมาตรา 10, 12, 13 ครบ |

ข้อจำกัด: verdict นี้รับรอง citation set และความสอดคล้องกับ evidence
ที่ส่ง ไม่ใช่การรับรองว่าครบทุกกฎหมายที่อาจเกี่ยวข้องกับเหตุการณ์จริง

## NitiBench open-book

### Echo

ทั้ง 9 ข้อผ่าน exact citation set เมื่อส่งเฉพาะมาตราที่ถูกต้อง คำตอบชุดนี้
สนับสนุนข้อสรุปว่าโมเดลเหมาะกับ open-book best case

### Selection

| Case | Verdict | เหตุผล |
|---|---|---|
| Guardian consent | ผ่าน | เลือก 1598/5 จาก 10 candidates ถูกต้อง |
| Digital token offer | ไม่ผ่าน | เลือก 22 แทน 62 แม้ 62 อยู่ใน context |
| Foreign business shareholding | ไม่ผ่าน | เลือก 15 แทน 13 |
| Liquidator fraud | ไม่ผ่าน | เลือกกฎหมายบริษัทมหาชน 214 แทนกฎหมายความผิดเกี่ยวกับนิติบุคคล 38 |
| Financial institution fraud | ผ่าน | เลือก 146 ถูกต้อง |
| Public company email | ผ่าน | เลือก 7/1 ถูกต้อง |
| Unlicensed futures exchange | ผ่าน | เลือก 132 ถูกต้อง |
| Future asset security | ผ่าน | เลือก 9 ถูกต้อง |
| Tax animal-feed import | ผ่านแบบมีเงื่อนไข | เลือก 81 ถูก แต่เพิ่ม 79/2 ทำให้ precision 50% |

## Closed-book

| Case | Verdict | เหตุผล |
|---|---|---|
| แบบรายงานหลักทรัพย์เท็จ | ไม่ผ่าน | ตอบ 264/265 แทน assertion 302/1 |
| ส่งออกกัญชาไม่มีใบอนุญาต | ไม่ผ่าน | ตอบ 102 แทน 46/78 |
| บุคคลต้องห้ามเข้าเมือง | ไม่ผ่านแบบ strict | รู้มาตราแม่ 12 แต่ไม่ระบุ (7)/(8) |
| ข้อมูลสุขภาพ PDPA | ไม่ผ่าน | ตอบ 24 แทน 26 |
| ร้านอาหาร/สถานบริการ | ไม่ผ่าน | ไม่ abstain และโยงประมวลกฎหมายที่ดินมาตรา 108 |

ตัวอย่างสี่ข้อแรกเป็น source-reported assertions จึงต้องตรวจ primary law
ก่อนใช้วัด legal truth แบบ definitive แต่ failure ด้าน exact section และ
abstention ยังสังเกตได้โดยตรง

## Legal essay

### Thinking off

**SEC/Bitkub — ผ่านแบบมีเงื่อนไข**

- พบมาตรา 76, 88(2), 94 ครบ
- แยกหัวข้อบริษัท กรรมการ เอกสารเท็จ และสถานะการกล่าวโทษ
- แต่กล่าวว่ากล่าวโทษ “ต่อสำนักงาน ก.ล.ต.” ทั้งที่โจทย์ระบุ บก.ปอศ.
- เพิ่มสำนักงาน ป.ป.ช. ในลำดับกระบวนการ ทั้งที่โจทย์ระบุพนักงานสอบสวน
  อัยการ และศาล
- อธิบายฐานความรับผิดบางส่วนกว้างกว่าข้อเท็จจริง/ตัวบทที่ให้

**NCB employee leak — ผ่านแบบมีเงื่อนไข**

- อ้างมาตรา 24 และ 54 ตรงข้อความ structural chunks
- ระบุโทษตรง evidence
- เสนอ log/access evidence ที่เป็นประโยชน์
- control remediation ซ้ำหลายข้อและยังขาด least privilege, purpose
  binding, DLP, alerting, incident response และ chain of custody

### Thinking on

**SEC/Bitkub — ผ่าน citation anchor แต่ไม่แนะนำเป็น default**

- พบมาตราที่โจทย์ให้ครบ
- ใช้เวลา 131.78 วินาทีและมี reasoning ภาษาอังกฤษปน
- เนื้อหายังขยายความเกิน statutory evidence

**NCB employee leak — ไม่ผ่าน citation selection**

- expected recall 50%
- evidence packet รุ่นก่อน optimize มี hard negatives จำนวนมาก
- คำตอบอ้างมาตราเกินและมี reasoning ภาษาอังกฤษปน

## General legal chat

**Conversation mechanics — ผ่าน**

- ใช้ session เดียวครบ 3 turns
- จำหัวข้อ consent และทำตามคำสั่งให้ย่อเป็น checklist 5 ข้อ
- ใช้ภาษาไทยต่อเนื่อง

**Legal precision — ผ่านแบบมีเงื่อนไข**

- turn แรกอธิบายหลัก consent ตามมาตรา 20 ได้
- แต่ใช้คำกว้างว่า “ธนาคารและบริษัทข้อมูลเครดิตต้องขอก่อนทุกครั้ง”
  โดยไม่แยก actor และข้อยกเว้นในมาตราให้ชัด
- turn 2–3 นำการเปิดเผยตามวรรคสองมาเป็นหลักฐานตรวจความยินยอม
  ทั้งที่เป็น exception workflow คนละเรื่อง
- checklist จึงควรใช้เป็น draft และให้ Legal/Compliance แก้ก่อนนำไปตรวจจริง

## คำวินิจฉัยรวม

OpenThai 2.0 Legal เหมาะที่สุดในงาน:

1. ตอบจากมาตราที่คัดถูกและมีจำนวนจำกัด
2. สรุป/อธิบายตัวบทแบบมี citation contract
3. ร่าง legal essay เมื่อโจทย์ระบุมาตรา หรือ RAG ส่งตัวบทครบ
4. สร้าง checklist เบื้องต้นพร้อม evidence ให้มนุษย์ตรวจ

ไม่ควรใช้ลำพังในงาน:

1. ระบุเลขมาตราจาก closed-book เพื่อใช้ตัดสินจริง
2. เลือกมาตราจาก hard negatives จำนวนมากโดยไม่มี validator
3. ยืนยันองค์ประกอบความผิด โทษ หรือสถานะคดีโดยไม่เปิด primary source
4. ออก legal opinion หรือ control conclusion อัตโนมัติ
