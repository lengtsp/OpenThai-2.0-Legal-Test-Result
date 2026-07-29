# OpenThai 2.0 Legal — 12k long-context NCB audit benchmark

- Model: `iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b`
- vLLM context: `12,288` tokens
- Maximum output: `4,096` tokens
- Thinking: disabled
- Evidence mode: exact section-level structural chunks
- GPU KV cache: `1,580,236` tokens; theoretical 12k concurrency: `128.60x`
- Mean generation time: `94.88s`
- Macro citation precision / recall: `89.7%` / `96.4%`
- Codex judge mean: `2.38/5`

Citation scores measure section-number grounding only. They do not prove that the legal interpretation is correct; the Codex judge findings below inspect substantive claims and completion.

| Scenario | Prompt | Output | Total | Finish | Citation P/R | Codex judge | Time |
|---|---:|---:|---:|---|---:|---:|---:|
| integrated-member-it-audit-program | 5915 | 3783 | 9698 | stop | 100%/100% | 2.0/5 | 130.35s |
| loan-broker-credit-model-governance | 5023 | 4090 | 9113 | stop | 86%/86% | 2.5/5 | 133.52s |
| unlawful-disclosure-incident-response | 3999 | 1816 | 5815 | stop | 86%/100% | 2.0/5 | 57.00s |
| integrated-criteria-first-guardrail | 6009 | 1835 | 7844 | stop | 88%/100% | 3.0/5 | 58.65s |

## Codex judge findings

| Scenario | Verdict | Evidence-backed finding |
|---|---|---|
| integrated-member-it-audit-program | ไม่ผ่านสำหรับใช้งานจริง | หยุดกลางคำแม้ finish=stop; เนื้อหาจริงไม่ถึงมาตรา 26-28; สร้างกำหนดแก้ไข 7/15/30 วันและ sample size โดยไม่แยกว่าเป็นข้อเสนอผู้ตรวจสอบ |
| loan-broker-credit-model-governance | ต้องแก้สาระสำคัญก่อนใช้ | ครอบคลุมหัวข้อกว้าง แต่ใช้มาตรา 20/28 ขัดกับผลของมาตรา 24/5, ขยาย log retention เป็น 5 ปี และกล่าวการแจ้ง 30 วันกว้างเกินตัวบท |
| unlawful-disclosure-incident-response | ไม่ผ่านด้าน legal grounding | ตอบอังกฤษแม้สั่งภาษาไทย; สร้างหน้าที่แจ้ง regulator และ mandatory timeline ตามมาตรา 54 ซึ่งไม่มีในตัวบท และตีความมาตรา 20(2) เป็น breach notification |
| integrated-criteria-first-guardrail | ดีขึ้นแต่ยังต้อง human review | ครอบคลุมครบ 7 มาตราและกระชับขึ้น แต่สร้างรอบทบทวน 6 เดือน, sample 100% และ due date 30/06/2024 โดยไม่ติดป้ายตามคำสั่ง; ย่อมาตรา 26 และละรายละเอียด log 2 ปี |

## Interpretation

- The 12,288-token service successfully accepted evidence packets that need about 9,100–10,000 prompt-plus-output tokens and would not fit the previous 8,192-token configuration with a 4,096-token output reserve.
- All requests returned `finish_reason=stop`, but one answer still ended mid-word. Therefore `stop` must not be used as the only completeness check.
- Larger context solved capacity, not groundedness. The model still invented deadlines, notification duties, sample sizes, and legal effects that were absent from the supplied sections.
- The criteria-first guardrail improved section coverage and reduced verbosity, but did not fully obey the rule to label auditor-designed values. Production use still requires deterministic post-validation and human legal review.

## integrated-member-it-audit-program

**Question:** จัดทำแผนตรวจสอบ IT Internal Audit ฉบับละเอียดสำหรับธนาคารที่เป็นสมาชิก NCB ให้ครอบคลุม governance, data quality, consent/purpose limitation, access control และ log retention, สิทธิและข้อโต้แย้งของลูกค้า, adverse credit decision, ขั้นตอน sampling, หลักฐานที่ต้องขอ, วิธีทดสอบ control, เกณฑ์จัดระดับข้อบกพร่อง และ remediation plan โดยแยก preventive/detective/corrective control และอ้างมาตราที่เกี่ยวข้องทุกหัวข้อ

**Supplied:** 17, 19, 20, 25, 26, 27, 28

**Cited:** 17, 19, 20, 25, 26, 27, 28

**Answer (130.35s, 3783 output tokens, finish=stop):**


**แผนตรวจสอบ IT Internal Audit ฉบับละเอียดสำหรับธนาคารที่เป็นสมาชิก NCB**
*อ้างอิงกฎหมาย: พระราชบัญญัติการประกอบธุรกิจข้อมูลเครดิต พ.ศ. ๒๕๔๕ (รวมฉบับแก้ไข ๑-๖) มาตรา ๑๗, ๑๙, ๒๐, ๒๕, ๒๖, ๒๗, ๒๘*

---

## 1. Governance (มาตรา ๑๗)
**วัตถุประสงค์**: ตรวจสอบระบบและข้อกำหนดการประมวลผลข้อมูลตามมาตรา ๑๗ เพื่อให้มั่นใจว่าบริษัทข้อมูลเครดิตและสมาชิกปฏิบัติตามหลักเกณฑ์ที่คณะกรรมการกำหนด

### 1.1 ขั้นตอน Sampling
- **ตัวอย่าง**: เลือกตัวอย่างบริษัทข้อมูลเครดิตและสมาชิกที่มีการประมวลผลข้อมูลขนาดใหญ่ (Big Data) อย่างน้อย ๕ ราย
- **วิธีการ**: ใช้ระบบสุ่ม (Random Sampling) จากฐานข้อมูลสมาชิกทั้งหมด

### 1.2 หลักฐานที่ต้องขอ
- เอกสารระบบและข้อกำหนดการประมวลผลข้อมูล (System and Control Documentation)
- รายงานการตรวจสอบภายในประจำปี (Internal Audit Report)
- นโยบายความปลอดภัยและความเป็นส่วนตัว (Security & Privacy Policy)

### 1.3 วิธีทดสอบ Control
| Control | วิธีทดสอบ | ผลการทดสอบ |
|--------|------------|--------------|
| ระบบจำแนกข้อมูล | ตรวจสอบเมตาดาต้าและโครงสร้างฐานข้อมูล | ผ่าน/ไม่ผ่าน |
| ระบบการแก้ไขข้อมูล | ตรวจสอบประวัติการแก้ไข (Audit Trail) | ผ่าน/ไม่ผ่าน |
| ระบบรักษาความลับ | ตรวจสอบการเข้าถึงข้อมูลโดยไม่มีสิทธิ (Unauthorized Access) | ผ่าน/ไม่ผ่าน |
| ระบบบันทึกการเข้าถึง | ตรวจสอบบันทึกการเข้าถึงข้อมูลภายใน ๒ ปี | ผ่าน/ไม่ผ่าน |

### 1.4 เกณฑ์จัดระดับข้อบกพร่อง
- **ระดับ ๑ (Critical)**: ไม่มีระบบจำแนกข้อมูลหรือระบบรักษาความลับ
- **ระดับ ๒ (High)**: ระบบจำแนกข้อมูลไม่ครบถ้วน หรือบันทึกการเข้าถึงไม่ครบกำหนดเวลา
- **ระดับ ๓ (Medium)**: ระบบการแก้ไขข้อมูลไม่มีการบันทึกประวัติ
- **ระดับ ๔ (Low)**: ระบบการตรวจสอบและรายงานไม่มีการตรวจสอบเป็นประจำ

### 1.5 Remediation Plan
- กำหนดให้บริษัทข้อมูลเครดิตปรับปรุงระบบจำแนกข้อมูลและระบบรักษาความลับภายใน ๓๐ วัน
- ติดตามผลการแก้ไขในรอบถัดไป (Follow-up Audit)

---

## 2. Data Quality (มาตรา ๑๙)
**วัตถุประสงค์**: ตรวจสอบความถูกต้องและความทันสมัยของข้อมูลตามมาตรา ๑๙

### 2.1 ขั้นตอน Sampling
- **ตัวอย่าง**: เลือกตัวอย่างข้อมูลลูกค้า ๑๐๐ ราย จากฐานข้อมูลทั้งหมด
- **วิธีการ**: ใช้ระบบสุ่ม (Random Sampling)

### 2.2 หลักฐานที่ต้องขอ
- รายงานการตรวจสอบความถูกต้องของข้อมูล (Data Accuracy Report)
- บันทึกการแก้ไขข้อมูล (Data Correction Log)
- นโยบายการจัดการข้อมูลคุณภาพ (Data Quality Policy)

### 2.3 วิธีทดสอบ Control
| Control | วิธีทดสอบ | ผลการทดสอบ |
|--------|------------|--------------|
| การรายงานข้อมูล | ตรวจสอบความถูกต้องของข้อมูลที่รายงาน | ผ่าน/ไม่ผ่าน |
| การแก้ไขข้อมูล | ตรวจสอบประวัติการแก้ไขและความถูกต้องหลังการแก้ไข | ผ่าน/ไม่ผ่าน |
| การตรวจสอบข้อโต้แย้ง | ตรวจสอบกระบวนการจัดการข้อโต้แย้งตามมาตรา ๑๙ (๔) | ผ่าน/ไม่ผ่าน |

### 2.4 เกณฑ์จัดระดับข้อบกพร่อง
- **ระดับ ๑ (Critical)**: ข้อมูลไม่ถูกต้องและไม่ได้แก้ไขภายใน ๓๐ วัน
- **ระดับ ๒ (High)**: ข้อมูลไม่ถูกต้องแต่ได้แก้ไขแล้ว
- **ระดับ ๓ (Medium)**: ข้อมูลขาดหายหรือไม่สมบูรณ์
- **ระดับ ๔ (Low)**: ข้อมูลถูกต้องแต่ไม่มีการตรวจสอบเป็นประจำ

### 2.5 Remediation Plan
- บริษัทข้อมูลเครดิตต้องแก้ไขข้อมูลที่ไม่ถูกต้องภายใน ๗ วัน
- จัดทำรายงานการแก้ไขและส่งให้คณะกรรมการภายใน ๑๕ วัน

---

## 3. Consent & Purpose Limitation (มาตรา ๒๐)
**วัตถุประสงค์**: ตรวจสอบการขอความยินยอมและการจำกัดวัตถุประสงค์การใช้ข้อมูลตามมาตรา ๒๐

### 3.1 ขั้นตอน Sampling
- **ตัวอย่าง**: เลือกตัวอย่างลูกค้า ๕๐ ราย ที่มีการขอใช้ข้อมูล
- **วิธีการ**: ใช้ระบบสุ่ม (Random Sampling)

### 3.2 หลักฐานที่ต้องขอ
- สำเนาหนังสือยินยอมของเจ้าของข้อมูล (Consent Form)
- รายงานการตรวจสอบการใช้ข้อมูล (Data Usage Report)
- นโยบายการจำกัดวัตถุประสงค์ (Purpose Limitation Policy)

### 3.3 วิธีทดสอบ Control
| Control | วิธีทดสอบ | ผลการทดสอบ |
|--------|------------|--------------|
| การขอใช้ข้อมูล | ตรวจสอบความถูกต้องของหนังสือยินยอม | ผ่าน/ไม่ผ่าน |
| การเปิดเผยข้อมูล | ตรวจสอบกรณีที่เปิดเผยข้อมูลโดยไม่จำเป็น | ผ่าน/ไม่ผ่าน |
| การแจ้งผลการตรวจสอบ | ตรวจสอบการแจ้งผลให้เจ้าของข้อมูลทราบ | ผ่าน/ไม่ผ่าน |

### 3.4 เกณฑ์จัดระดับข้อบกพร่อง
- **ระดับ ๑ (Critical)**: ไม่มีหนังสือยินยอมหรือเปิดเผยข้อมูลโดยไม่มีเหตุผล
- **ระดับ ๒ (High)**: ไม่มีการแจ้งผลการตรวจสอบให้เจ้าของข้อมูลทราบ
- **ระดับ ๓ (Medium)**: กรณีเปิดเผยข้อมูลไม่ได้รับความเห็นชอบจากคณะกรรมการ
- **ระดับ ๔ (Low)**: กรณีใช้ข้อมูลนอกวัตถุประสงค์แต่ไม่มีการละเมิดกฎหมาย

### 3.5 Remediation Plan
- บริษัทข้อมูลเครดิตต้องจัดทำหนังสือยินยอมและแจ้งผลการตรวจสอบภายใน ๗ วัน
- หากพบการละเมิดวัตถุประสงค์ ให้รายงานต่อคณะกรรมการเพื่อพิจารณา

---

## 4. Access Control (มาตรา ๑๗)
**วัตถุประสงค์**: ตรวจสอบการควบคุมการเข้าถึงข้อมูลตามมาตรา ๑๗

### 4.1 ขั้นตอน Sampling
- **ตัวอย่าง**: เลือกตัวอย่างสมาชิก ๒๐ ราย ที่มีการเข้าถึงข้อมูล
- **วิธีการ**: ใช้ระบบสุ่ม (Random Sampling)

### 4.2 หลักฐานที่ต้องขอ
- บันทึกการเข้าถึงข้อมูล (Access Log)
- นโยบายการควบคุมการเข้าถึง (Access Control Policy)
- รายงานการตรวจสอบการเข้าถึง (Access Audit Report)

### 4.3 วิธีทดสอบ Control
| Control | วิธีทดสอบ | ผลการทดสอบ |
|--------|------------|--------------|
| การบันทึกการเข้าถึง | ตรวจสอบบันทึกการเข้าถึงภายใน ๒ ปี | ผ่าน/ไม่ผ่าน |
| การรักษาความลับ | ตรวจสอบการเข้าถึงข้อมูลโดยไม่มีสิทธิ | ผ่าน/ไม่ผ่าน |
| การทำลายข้อมูล | ตรวจสอบการทำลายข้อมูลที่เกินกำหนดเวลา | ผ่าน/ไม่ผ่าน |

### 4.4 เกณฑ์จัดระดับข้อบกพร่อง
- **ระดับ ๑ (Critical)**: ไม่มีการบันทึกการเข้าถึงข้อมูล
- **ระดับ ๒ (High)**: บันทึกการเข้าถึงข้อมูลไม่ครบถ้วนหรือไม่มีการตรวจสอบ
- **ระดับ ๓ (Medium)**: การรักษาความลับไม่เพียงพอ
- **ระดับ ๔ (Low)**: การทำลายข้อมูลไม่เป็นไปตามกำหนดเวลา

### 4.5 Remediation Plan
- บริษัทข้อมูลเครดิตต้องปรับปรุงระบบบันทึกการเข้าถึงและการรักษาความลับภายใน ๑๕ วัน
- ติดตามผลการแก้ไขในรอบถัดไป (Follow-up Audit)

---

## 5. Log Retention (มาตรา ๑๗)
**วัตถุประสงค์**: ตรวจสอบการบันทึกและรักษาไว้ซึ่งบันทึกการเข้าถึงข้อมูลตามมาตรา ๑๗

### 5.1 ขั้นตอน Sampling
- **ตัวอย่าง**: เลือกตัวอย่างบันทึกการเข้าถึงข้อมูล ๑๐ รายการ
- **วิธีการ**: ใช้ระบบสุ่ม (Random Sampling)

### 5.2 หลักฐานที่ต้องขอ
- บันทึกการเข้าถึงข้อมูล (Access Log) ที่มีอายุเกิน ๒ ปี
- นโยบายการรักษาไว้ซึ่งบันทึก (Log Retention Policy)

### 5.3 วิธีทดสอบ Control
| Control | วิธีทดสอบ | ผลการทดสอบ |
|--------|------------|--------------|
| การบันทึกการเข้าถึง | ตรวจสอบว่าบันทึกการเข้าถึงมีอายุเกิน ๒ ปีหรือไม่ | ผ่าน/ไม่ผ่าน |
| การทำลายข้อมูล | ตรวจสอบการทำลายข้อมูลที่เกินกำหนดเวลา | ผ่าน/ไม่ผ่าน |

### 5.4 เกณฑ์จัดระดับข้อบกพร่อง
- **ระดับ ๑ (Critical)**: ไม่มีการบันทึกการเข้าถึงข้อมูลหรือทำลายก่อนกำหนดเวลา
- **ระดับ ๒ (High)**: บันทึกการเข้าถึงข้อมูลไม่ครบถ้วนหรือไม่มีการตรวจสอบ
- **ระดับ ๓ (Medium)**: การทำลายข้อมูลไม่เป็นไปตามกำหนดเวลา
- **ระดับ ๔ (Low)**: บันทึกการเข้าถึงข้อมูลมีอายุไม่ถึง ๒ ปี

### 5.5 Remediation Plan
- บริษัทข้อมูลเครดิตต้องปรับปรุงระบบบันทึกและทำลายข้อมูลภายใน ๑๕ วัน
- จัดทำรายงานการแก้ไขและส่งให้คณะกรรมการภายใน ๓๐ วัน

---

## 6. สิทธิและข้อโต้แย้งของลูกค้า (มาตรา ๒๕)
**วัตถุประสงค์**: ตรวจสอบสิทธิของเจ้าของข้อมูลและการจัดการข้อโต้แย้งตามมาตรา ๒๕

### 6.1 ขั้นตอน Sampling
- **ตัวอย่าง**: เลือกตัวอย่างเจ้าของข้อมูล ๕๐ ราย ที่มีการใช้สิทธิ
- **วิธีการ**: ใช้ระบบสุ่ม (Random Sampling)

### 6.2 หลักฐานที่ต้องขอ
- รายงานการตรวจสอบสิทธิของเจ้าของข้อมูล (Rights Audit Report)
- บันทึกการตรวจสอบข้อมูล (Data Verification Log)
- นโยบายการจัดการสิทธิของเจ้าของข้อมูล (Rights Management Policy)

### 6.3 วิธีทดสอบ Control
| Control | วิธีทดสอบ | ผลการทดสอบ |
|--------|------------|--------------|
| การตรวจสอบข้อมูล | ตรวจสอบความถูกต้องของข้อมูลที่เจ้าของข้อมูลตรวจสอบ | ผ่าน/ไม่ผ่าน |
| การแจ้งผลการตรวจสอบ | ตรวจสอบการแจ้งผลให้เจ้าของข้อมูลทราบ | ผ่าน/ไม่ผ

## loan-broker-credit-model-governance

**Question:** ออกแบบ audit work program ฉบับเต็มสำหรับกระบวนการรับข้อมูล NCB ผ่านผู้ประกอบธุรกิจเป็นตัวกลางในการจัดหาสินเชื่อและการสร้าง credit model ครอบคลุม consent lifecycle, onward disclosure, data minimisation/de-identification, model purpose limitation, access/security/logging, adverse decision, audit evidence, test procedure, exception examples, risk rating และข้อเสนอแนะ โดยอธิบายผลของมาตรา 24/5 ที่มีต่อมาตรา 20 และ 28 ให้ชัดเจน

**Supplied:** 17, 20, 24/1, 24/2, 24/3, 24/4, 24/5

**Cited:** 20, 24/1, 24/2, 24/3, 24/4, 24/5, 28

**Answer (133.52s, 4090 output tokens, finish=stop):**


# Audit Work Program: การรับข้อมูล NCB ผ่านผู้ประกอบธุรกิจเป็นตัวกลางในการจัดหาสินเชื่อและการสร้าง Credit Model
**อ้างอิงกฎหมาย:** พระราชบัญญัติการประกอบธุรกิจข้อมูลเครดิต พ.ศ. ๒๕๔๕ (รวมฉบับแก้ไข ๑-๖)

---

## **1. บทนำ**
การรับข้อมูล NCB ผ่านผู้ประกอบธุรกิจเป็นตัวกลางในการจัดหาสินเชื่อและการสร้าง Credit Model เป็นกระบวนการสำคัญที่ต้องปฏิบัติตามกฎหมายอย่างเคร่งครัด เพื่อป้องกันการละเมิดสิทธิของเจ้าของข้อมูลและรักษาความน่าเชื่อถือของระบบข้อมูลเครดิต การออกแบบ Audit Work Program นี้ครอบคลุมขั้นตอนสำคัญตั้งแต่ **Consent Lifecycle** จนถึง **Adverse Decision** พร้อมการตรวจสอบ **Audit Evidence** และการประเมิน **Risk Rating** โดยอ้างอิงมาตรา ๒๐ และมาตรา ๒๘ เป็นหลัก

---

## **2. ขอบเขตการตรวจสอบ**
- **ข้อมูลที่รับจากสมาชิกประเภทผู้ประกอบธุรกิจเป็นตัวกลาง** (มาตรา ๒๔/๑)
- **การสร้าง Credit Model** โดยใช้ข้อมูลจากสมาชิกดังกล่าว (มาตรา ๒๔/๓)
- **การเปิดเผยข้อมูล** ตามมาตรา ๒๐ และมาตรา ๒๔/๒
- **การปฏิเสธการให้บริการ** (Adverse Decision) ตามมาตรา ๒๔/๔
- **การยกเว้นการปฏิบัติตามมาตรา ๒๐ และ ๒๘** ตามมาตรา ๒๔/๕

---

## **3. กระบวนการ Audit Work Program**

### **3.1 Consent Lifecycle (มาตรา ๒๐)**
**วัตถุประสงค์:** ตรวจสอบว่าสมาชิกได้รับความยินยอมจากเจ้าของข้อมูลก่อนเปิดเผยข้อมูลหรือไม่

#### **ขั้นตอนการตรวจสอบ:**
1. **ตรวจสอบระบบ Consent Lifecycle:**
   - ตรวจสอบว่าระบบมีการบันทึก **Consent** (ความยินยอม) จากเจ้าของข้อมูลทุกครั้งที่เปิดเผยข้อมูล
   - ตรวจสอบว่ามีการบันทึก **วันที่/เวลา** และ **ตัวตนของเจ้าของข้อมูล** ที่ให้ความยินยอม
   - ตรวจสอบว่ามีการแจ้งให้เจ้าของข้อมูลทราบภายใน **30 วัน** หลังการเปิดเผยข้อมูล (มาตรา ๒๐ วรรคสอง)

2. **ตรวจสอบข้อยกเว้น (Exception):**
   - ตรวจสอบกรณีที่ไม่ต้องได้รับความยินยอมตามมาตรา ๒๐ วรรคสอง ได้แก่:
     - คำสั่งศาลหรือหมายศาล (มาตรา ๒๐ วรรคสอง (๑))
     - หนังสือจากพนักงานสอบสวนเพื่อประโยชน์ในการสอบสวนคดีอาญา (มาตรา ๒๐ วรรคสอง (๒))
     - หนังสือจากกระทรวงการคลัง ธนาคารแห่งประเทศไทย หรือคณะกรรมการกำกับหลักทรัพย์ฯ (มาตรา ๒๐ วรรคสอง (๓))
   - ตรวจสอบว่าสมาชิกได้รับ **ความเห็นชอบจากคณะกรรมการ** ก่อนเปิดเผยข้อมูลในกรณีดังกล่าว (มาตรา ๒๐ วรรคสอง)

3. **ตรวจสอบการเปิดเผยข้อมูลแก่สมาชิกประเภทผู้ประกอบธุรกิจเป็นตัวกลาง (มาตรา ๒๔/๑):**
   - ตรวจสอบว่าสมาชิกได้รับความยินยอมจากเจ้าของข้อมูลก่อนเปิดเผยข้อมูล
   - ตรวจสอบว่าข้อมูลที่เปิดเผยเป็นไปตาม **หลักเกณฑ์ วิธีการ และเงื่อนไข** ที่คณะกรรมการกำหนด

---

### **3.2 Onward Disclosure (มาตรา ๒๐)**
**วัตถุประสงค์:** ตรวจสอบว่าสมาชิกเปิดเผยข้อมูลแก่ผู้ที่จะให้สินเชื่อโดยไม่จำเป็นต้องได้รับความยินยอมก่อนหรือไม่

#### **ขั้นตอนการตรวจสอบ:**
1. **ตรวจสอบกรณีที่ไม่ต้องได้รับความยินยอม:**
   - ตรวจสอบว่าสมาชิกเปิดเผยข้อมูลแก่ผู้ที่จะให้สินเชื่อในกรณีดังต่อไปนี้:
     - คำสั่งศาลหรือหมายศาล (มาตรา ๒๐ วรรคสอง (๑))
     - หนังสือจากพนักงานสอบสวน (มาตรา ๒๐ วรรคสอง (๒))
     - หนังสือจากกระทรวงการคลัง ธนาคารแห่งประเทศไทย หรือคณะกรรมการกำกับหลักทรัพย์ฯ (มาตรา ๒๐ วรรคสอง (๓))
   - ตรวจสอบว่าสมาชิกได้รับ **ความเห็นชอบจากคณะกรรมการ** ก่อนเปิดเผยข้อมูลในกรณีดังกล่าว

2. **ตรวจสอบการแจ้งให้เจ้าของข้อมูลทราบ:**
   - ตรวจสอบว่าสมาชิกได้แจ้งให้เจ้าของข้อมูลทราบภายใน **30 วัน** หลังการเปิดเผยข้อมูล (มาตรา ๒๐ วรรคสอง)

---

### **3.3 Data Minimisation & De-identification (มาตรา ๒๐)**
**วัตถุประสงค์:** ตรวจสอบว่าสมาชิกได้รับข้อมูลเฉพาะที่จำเป็นและได้ทำการลบข้อมูลที่ระบุตัวตนแล้วหรือไม่

#### **ขั้นตอนการตรวจสอบ:**
1. **ตรวจสอบข้อมูลที่รับจากสมาชิก:**
   - ตรวจสอบว่าสมาชิกได้รับข้อมูลเฉพาะส่วนที่จำเป็นสำหรับการวิเคราะห์สินเชื่อและการออกบัตรเครดิต (มาตรา ๒๐)
   - ตรวจสอบว่าสมาชิกได้ทำการ **ลบข้อมูลที่ระบุตัวตน** (De-identification) ก่อนใช้ข้อมูลในการสร้าง Credit Model

2. **ตรวจสอบการใช้ข้อมูลใน Credit Model (มาตรา ๒๔/๓):**
   - ตรวจสอบว่าสมาชิกใช้ข้อมูลเฉพาะส่วนที่ไม่มีข้อมูลที่ระบุตัวตนของเจ้าของข้อมูล
   - ตรวจสอบว่าสมาชิกได้รับความยินยอมจากเจ้าของข้อมูลก่อนใช้ข้อมูลในการสร้าง Credit Model

---

### **3.4 Model Purpose Limitation (มาตรา ๒๐)**
**วัตถุประสงค์:** ตรวจสอบว่าสมาชิกใช้ข้อมูลใน Credit Model เฉพาะเพื่อประโยชน์ในการวิเคราะห์สินเชื่อและการออกบัตรเครดิตเท่านั้น

#### **ขั้นตอนการตรวจสอบ:**
1. **ตรวจสอบวัตถุประสงค์ของการใช้ข้อมูล:**
   - ตรวจสอบว่าสมาชิกใช้ข้อมูลใน Credit Model เฉพาะเพื่อประโยชน์ในการวิเคราะห์สินเชื่อและการออกบัตรเครดิต
   - ตรวจสอบว่าสมาชิกไม่ใช้ข้อมูลในวัตถุประสงค์อื่นที่ไม่ได้รับอนุญาต

2. **ตรวจสอบการอนุญาตจากคณะกรรมการ (มาตรา ๒๔/๓):**
   - ตรวจสอบว่าสมาชิกได้รับอนุญาตจากคณะกรรมการให้ใช้แบบจำลอง Credit Model ในการวิเคราะห์สินเชื่อและการออกบัตรเครดิต

---

### **3.5 Access, Security, Logging (มาตรา ๒๐)**
**วัตถุประสงค์:** ตรวจสอบว่าระบบมีการรักษาความปลอดภัยและบันทึกการเข้าถึงข้อมูลอย่างถูกต้องหรือไม่

#### **ขั้นตอนการตรวจสอบ:**
1. **ตรวจสอบระบบรักษาความปลอดภัย:**
   - ตรวจสอบว่าระบบมีการรักษาความลับและความปลอดภัยของข้อมูลเพื่อป้องกันการนำข้อมูลไปใช้ผิดวัตถุประสงค์
   - ตรวจสอบว่าระบบมีการป้องกันการแก้ไขข้อมูลโดยไม่ชอบหรือโดยไม่ได้รับอนุญาต

2. **ตรวจสอบระบบบันทึกการเข้าถึงข้อมูล:**
   - ตรวจสอบว่าระบบบันทึกการเข้าถึงข้อมูลโดยมีกำหนดระยะเวลาไม่น้อยกว่า **2 ปี** (มาตรา ๒๐)
   - ตรวจสอบว่าระบบมีการบันทึก **วันที่/เวลา** และ **ตัวตนของผู้เข้าถึงข้อมูล**

---

### **3.6 Adverse Decision (มาตรา ๒๔/๔)**
**วัตถุประสงค์:** ตรวจสอบว่าสมาชิกแสดงเหตุผลในการปฏิเสธการให้บริการและแหล่งที่มาของข้อมูลเมื่อปฏิเสธการให้บริการ

#### **ขั้นตอนการตรวจสอบ:**
1. **ตรวจสอบการปฏิเสธการให้บริการ:**
   - ตรวจสอบว่าสมาชิกแสดงเหตุผลในการปฏิเสธการให้บริการแก่ลูกค้าผู้ขอสินเชื่อ
   - ตรวจสอบว่าสมาชิกแสดงแหล่งที่มาของข้อมูลที่ใช้ในการปฏิเสธการให้บริการ

2. **ตรวจสอบสิทธิของเจ้าของข้อมูล:**
   - ตรวจสอบว่าลูกค้ามีสิทธิตรวจสอบความถูกต้องของข้อมูลโดยไม่ต้องเสียค่าธรรมเนียมภายใน **30 วัน** หลังการปฏิเสธการให้บริการ

---

### **3.7 Audit Evidence**
**วัตถุประสงค์:** ตรวจสอบว่ามีเอกสารหรือหลักฐานที่พิสูจน์การปฏิบัติตามกฎหมายหรือไม่

#### **ขั้นตอนการตรวจสอบ:**
1. **ตรวจสอบเอกสาร Consent:**
   - ตรวจสอบสำเนา Consent ที่ได้รับจากเจ้าของข้อมูล
   - ตรวจสอบวันที่/เวลาและตัวตนของเจ้าของข้อมูลที่ให้ความยินยอม

2. **ตรวจสอบเอกสารการแจ้งให้ทราบ:**
   - ตรวจสอบสำเนาหนังสือแจ้งให้เจ้าของข้อมูลทราบภายใน 30 วัน

3. **ตรวจสอบเอกสารการปฏิเสธการให้บริการ:**
   - ตรวจสอบสำเนาหนังสือแสดงเหตุผลในการปฏิเสธการให้บริการและแหล่งที่มาของข้อมูล

---

## **4. การประเมิน Risk Rating**
| **ปัจจัย** | **ระดับ Risk** | **คำอธิบาย** |
|------------|----------------|--------------|
| **Consent Lifecycle** | ต่ำ | ระบบมีการบันทึก Consent ทุกครั้งและแจ้งให้เจ้าของข้อมูลทราบภายใน 30 วัน |
| **Onward Disclosure** | ต่ำ | สมาชิกเปิดเผยข้อมูลตามข้อยกเว้นและได้รับความเห็นชอบจากคณะกรรมการ |
| **Data Minimisation** | ต่ำ | สมาชิกใช้ข้อมูลเฉพาะส่วนที่จำเป็นและลบข้อมูลที่ระบุตัวตนแล้ว |
| **Model Purpose Limitation** | ต่ำ | สมาชิกใช้ข้อมูลเฉพาะเพื่อประโยชน์ในการวิเคราะห์สินเชื่อและการออกบัตรเครดิต |
| **Access/Security** | ต่ำ | ระบบมีการรักษาความปลอดภัยและบันทึกการเข้าถึงข้อมูลอย่างถูกต้อง |
| **Adverse Decision** | ต่ำ | สมาชิกแสดงเหตุผลและแหล่งที่มาของข้อมูลเมื่อปฏิเสธการให้บริการ |

---

## **5. ข้อเสนอแนะ**
1. **ปรับปรุงระบบ Consent Lifecycle:**
   - เพิ่มการตรวจสอบอัตโนมัติว่าสมาชิกได้รับความยินยอมจากเจ้าของข้อมูลก่อนเปิดเผยข้อมูล
   - บังคับให้สมาชิกต้องแจ้งให้เจ้าของข้อมูลทราบภายใน 30 วัน หลังการเปิดเผยข้อมูล

2. **เพิ่มการตรวจสอบการอนุญาตจากคณะกรรมการ:**
   - ตรวจสอบว่าสมาชิกได้รับความเห็นชอบจากคณะกรรมการก่อนเปิดเผยข้อมูลในกรณีที่ไม่ต้องได้รับความยินยอม

3. **ปรับปรุงระบบบันทึกการเข้าถึงข้อมูล:**
   - ขยายระยะเวลาการบันทึกการเข้าถึงข้อมูลจาก 2 ปี เป็น 5 ปี เพื่อเพิ่มความโปร่งใส

4. **ตรวจสอบการใช้ข้อมูลใน Credit Model:**
   - ตรวจสอบว่าสมาชิกใช้ข้อมูลเฉพาะเพื่อประโยชน์ในการวิเคราะห์สินเชื่อและการออกบัตรเครดิตเท่านั้น

5. **ปรับปรุงระบบรักษาความปลอดภัย:**
   - เพิ่มการตรวจสอบการป้องกันการแก้ไขข้อมูลโดยไม่ชอบหรือโดยไม่ได้รับอนุญาต

---

## **6. สรุป**
การตรวจสอบการรับข้อมูล NCB ผ่านผู้ประกอบธุรกิจเป็นตัวกลางในการจัดหาสินเชื่อและการสร้าง Credit Model ต้องปฏิบัติตามมาตรา ๒๐ และมาตรา ๒๘ อย่างเคร่งครัด โดยมี重点ที่ **Consent Lifecycle**, **Onward Disclosure**, **Data Minimisation**, **Model Purpose Limitation**, **Access/Security**, และ **Adverse Decision** การออกแบบ Audit Work Program นี้ช่วยให้ธนาคารสามารถตรวจสอบความถูกต้องของการปฏิบัติตามกฎหมายและลดความเสี่ยงจากการละเมิดสิทธิของเจ้าของข้อมูลได้อย่างมีประสิทธิภาพ

## unlawful-disclosure-incident-response

**Question:** สมมุติพบเหตุพนักงานส่งรายงานข้อมูลเครดิตให้บุคคลภายนอกที่ไม่มีสิทธิ ให้จัดทำ incident assessment และ audit finding ฉบับละเอียด ตั้งแต่การรักษาหลักฐาน log/email/file transfer, การพิสูจน์สิทธิและ consent, การแยก civil/criminal exposure, root cause, affected population, containment, notification/escalation, corrective action, owner/due date และ follow-up test โดยห้ามสรุปเกินข้อความกฎหมาย

**Supplied:** 17, 20, 41, 51, 53, 54

**Cited:** 17, 20, 24, 41, 51, 53, 54

**Answer (57.00s, 1816 output tokens, finish=stop):**


**Incident Assessment & Audit Finding: Unauthorized Disclosure of Credit Information**
*Based on the Credit Information Act B.E. 2545 (No. 1-6), Sections 17, 20, 41, 51, 53, and 54*

---

### **1. Evidence Preservation (Log/Email/File Transfer)**
**Legal Basis:**
- **Section 17(6)**: Requires logging all data access with timestamps for at least 2 years.
- **Section 20(2)**: Mandates written consent from data owners before disclosure.
- **Section 53**: Penalties for unauthorized disclosure of data.

**Audit Evidence:**
- **Log Files**: Extract system logs (e.g., SIEM, database audit trails) showing timestamps, user IDs, and IP addresses of all data accesses.
- **Email/Transfer Records**: Preserve email trails, file transfer logs (e.g., SFTP, email attachments), and metadata (sender/receiver details, timestamps).
- **Consent Documentation**: Verify if written consent from data owners was obtained (per Section 20(1)). If absent, document the breach of Section 20(1).

**Gap Analysis:**
- If logs/emails are incomplete or missing, this constitutes an **evidence gap** under Section 17(6) and Section 20(1), as the bank failed to maintain adequate access controls and consent records.

---

### **2. Proof of Rights and Consent**
**Legal Basis:**
- **Section 20(1)**: Disclosure requires explicit written consent from data owners.
- **Section 53**: Unauthorized disclosure is a criminal offense.

**Audit Evidence:**
- **Consent Records**: Review signed consent forms or digital consent logs (e.g., CRM systems) for the affected data owners.
- **Access Control Lists (ACLs)**: Verify if the employee had legitimate access rights to the data (per Section 17(1)).
- **Internal Policies**: Check if the bank’s data access policies align with Section 20(1) requirements.

**Gap Analysis:**
- If consent records are missing or ACLs were misconfigured, this violates Section 20(1) and Section 17(1), exposing the bank to civil liability under Section 41.

---

### **3. Civil vs. Criminal Exposure**
**Legal Basis:**
- **Section 41**: Civil liability for incorrect/unauthorized disclosure causing harm.
- **Section 53**: Criminal liability for intentional/unauthorized disclosure.
- **Section 54**: Criminal liability for violating Section 24 (e.g., sharing data with unauthorized parties).

**Audit Findings:**
- **Civil Exposure**: If the disclosure caused financial loss to data owners (e.g., fraud), the bank is liable for damages under Section 41.
- **Criminal Exposure**: If the employee acted with intent (Section 53) or violated Section 24 (e.g., sharing with third parties), criminal charges under Section 54 apply.

**Gap Analysis:**
- Failure to segregate civil/criminal exposure in the report violates Section 17(6)’s requirement for systematic data management.

---

### **4. Root Cause Analysis**
**Legal Basis:**
- **Section 17**: Systemic failures in data access controls.
- **Section 20**: Lack of consent procedures.

**Root Causes Identified:**
- **Inadequate Access Controls**: Employee had excessive permissions (violating Section 17(1)).
- **Missing Consent Workflow**: No documented process for obtaining data owner consent (Section 20(1)).
- **Training Deficiency**: Employee lacked awareness of Section 20 and Section 53 penalties.

**Gap Analysis:**
- Root causes stem from poor governance under Section 17, requiring systemic fixes beyond individual disciplinary action.

---

### **5. Affected Population**
**Legal Basis:**
- **Section 17**: Scope of data types subject to logging and access controls.
- **Section 20**: Disclosure affects data owners’ rights.

**Affected Parties:**
- **Data Owners**: Individuals whose credit data was disclosed without consent.
- **Bank**: Liable for civil damages (Section 41) and criminal penalties (Section 53/54).
- **Third Parties**: Recipients of the disclosed data (if identifiable).

**Gap Analysis:**
- Failure to identify all affected parties violates Section 17(6)’s requirement for comprehensive access logging.

---

### **6. Containment Measures**
**Immediate Actions:**
- **Disable Employee Access**: Revoke system privileges per Section 17(1).
- **Freeze Data Transfers**: Halt all external data exports until investigation concludes.
- **Notify Legal Team**: Escalate to compliance officers for Section 53/54 liability assessment.

**Gap Analysis:**
- Delayed containment (e.g., failing to revoke access within 24 hours) exacerbates civil liability under Section 41.

---

### **7. Notification & Escalation**
**Legal Requirements:**
- **Section 20(2)**: Notify data owners in writing within 30 days of discovery.
- **Section 54**: Notify regulators (e.g., Bank of Thailand) if criminal breach is confirmed.

**Audit Findings:**
- **Internal Notification**: Bank failed to notify affected data owners within 30 days (Section 20(2)).
- **External Notification**: No report to regulators despite criminal intent (Section 54).

**Gap Analysis:**
- Non-compliance with Section 20(2) and Section 54 exposes the bank to dual penalties.

---

### **8. Corrective Actions**
**Short-Term Fixes:**
- Terminate/retrain the employee for violating Section 53.
- Implement mandatory consent workflows for all data accesses (Section 20).

**Long-Term Solutions:**
- Upgrade access control systems to meet Section 17(1) standards.
- Conduct annual audits of data access logs (Section 17(6)).

**Gap Analysis:**
- Superficial fixes (e.g., retraining without system upgrades) fail to address root causes under Section 17.

---

### **9. Ownership & Deadlines**
**Responsibility Matrix:**
| **Action**               | **Owner**         | **Deadline** |
|--------------------------|-------------------|--------------|
| Revoke employee access   | IT Security       | 24 hours     |
| Notify data owners       | Compliance Dept.  | 30 days      |
| Regulatory report        | Legal Counsel     | 15 days      |
| System upgrade           | CTO               | 90 days      |

**Gap Analysis:**
- Missing deadlines for regulatory notification violate Section 54’s mandatory timelines.

---

### **10. Follow-Up Test**
**Audit Procedures:**
1. **Test 1**: Verify 100% of new data access logs include timestamps and user IDs (Section 17(6)).
2. **Test 2**: Confirm 100% of data disclosures have documented consent (Section 20(1)).
3. **Test 3**: Validate regulator notification logs for Section 54 breaches.

**Expected Outcome:**
- 100% compliance with Sections 17, 20, and 54.
- Zero repeat incidents within 6 months.

---
**Conclusion**: The incident violates Sections 17, 20, 41, 53, and 54. Root causes require systemic fixes (access controls, consent workflows) rather than individual blame. Immediate containment and regulatory notification are critical to mitigate civil and criminal liability.

## integrated-criteria-first-guardrail

**Question:** จัดทำ IT Internal Audit work program สำหรับธนาคารที่เป็นสมาชิก NCB โดยทำตามลำดับนี้อย่างเคร่งครัด: (1) ตาราง Legal Criteria ต้องมีหนึ่งแถวต่อมาตรา 17, 19, 20, 25, 26, 27 และ 28 และห้ามเพิ่มข้อกำหนดที่ไม่มีในตัวบท (2) ตาราง Control/Evidence/Test แยกจากข้อกฎหมาย (3) ค่า sample size, risk rating, owner, due date หรือ remediation ทุกค่าที่ผู้ตรวจสอบออกแบบเองต้องติดป้ายว่า 'ข้อเสนอผู้ตรวจสอบ—ไม่ใช่กำหนดเวลาตามกฎหมาย' (4) ตอบภาษาไทยเท่านั้น (5) ห้ามสร้างหน้าที่แจ้ง regulator หรือ deadline ใหม่ และ (6) ปิดท้ายด้วย coverage checklist ครบทั้งเจ็ดมาตราและรายการ evidence gap

**Supplied:** 17, 19, 20, 25, 26, 27, 28

**Cited:** 17, 18, 19, 20, 25, 26, 27, 28

**Answer (58.65s, 1835 output tokens, finish=stop):**


### ตาราง Legal Criteria (มาตรา 17, 19, 20, 25, 26, 27, 28)

| มาตรา | ข้อกำหนดทางกฎหมาย | หลักฐานตรวจสอบ | วิธีทดสอบ Control | Evidence Gap | ข้อเสนอแนะ |
|--------|----------------------|------------------|---------------------|--------------|------------|
| **มาตรา 17** | บริษัทข้อมูลเครดิตต้องจัดระบบและข้อกำหนดดังต่อไปนี้: (1) ระบบจำแนกข้อมูล (2) ระบบการแก้ไขข้อมูล (3) ระบบรักษาความลับและความปลอดภัย (4) ระบบการขอใช้ข้อมูลและรายงาน (5) ระบบการตรวจสอบและแก้ไขข้อมูลของเจ้าของข้อมูล (6) ระบบบันทึกและรายงานผลการเข้าถึงข้อมูล (7) ระบบการทำลายข้อมูล | รายงานการตรวจสอบระบบ (Audit Report) | ตรวจสอบการเข้าถึงระบบข้อมูลและบันทึกการเข้าถึง (Log Review) | - | ตรวจสอบระบบการบันทึกและรายงานผลการเข้าถึงข้อมูลอย่างน้อยทุก 6 เดือน |
| **มาตรา 19** | สมาชิกต้องรายงานและส่งข้อมูลตามมาตรา 18 ให้บริษัทข้อมูลเครดิต และแจ้งลูกค้าโดยไม่เลือกปฏิบัติ | รายงานการส่งข้อมูล (Data Submission Report) | ตรวจสอบรายงานการส่งข้อมูลของสมาชิกและตรวจสอบความถูกต้องของข้อมูล | - | ตรวจสอบความถูกต้องของข้อมูลที่สมาชิกส่งให้บริษัทข้อมูลเครดิต |
| **มาตรา 20** | บริษัทข้อมูลเครดิตต้องเปิดเผยข้อมูลแก่สมาชิกหรือผู้ใช้บริการที่ขอใช้ข้อมูล โดยได้รับความยินยอมจากเจ้าของข้อมูล | บันทึกการขอใช้ข้อมูลและความยินยอม (Consent Records) | ตรวจสอบบันทึกการขอใช้ข้อมูลและตรวจสอบความยินยอมของเจ้าของข้อมูล | - | ตรวจสอบความถูกต้องของความยินยอมในการขอใช้ข้อมูล |
| **มาตรา 25** | เจ้าของข้อมูลมีสิทธิตรวจสอบและแก้ไขข้อมูลที่ไม่ถูกต้อง | บันทึกการตรวจสอบและแก้ไขข้อมูล (Data Verification Records) | ตรวจสอบบันทึกการตรวจสอบและแก้ไขข้อมูลของเจ้าของข้อมูล | - | ตรวจสอบความถูกต้องของข้อมูลที่เจ้าของข้อมูลขอแก้ไข |
| **มาตรา 26** | บริษัทข้อมูลเครดิตต้องพิจารณาคำขอและตรวจสอบข้อมูลภายใน 30 วัน | รายงานการตรวจสอบและแก้ไขข้อมูล (Audit Report) | ตรวจสอบระยะเวลาในการพิจารณาคำขอและตรวจสอบข้อมูล | - | ตรวจสอบระยะเวลาในการพิจารณาคำขอและตรวจสอบข้อมูล |
| **มาตรา 27** | บริษัทข้อมูลเครดิตต้องบันทึกข้อโต้แย้งและหลักฐานประกอบ | บันทึกข้อโต้แย้ง (Dispute Records) | ตรวจสอบบันทึกข้อโต้แย้งและหลักฐานประกอบ | - | ตรวจสอบความถูกต้องของข้อโต้แย้งและหลักฐานประกอบ |
| **มาตรา 28** | สถาบันการเงิน สมาชิก หรือผู้ใช้บริการต้องแสดงเหตุผลในการปฏิเสธการให้สินเชื่อ | รายงานการปฏิเสธการให้สินเชื่อ (Credit Denial Report) | ตรวจสอบรายงานการปฏิเสธการให้สินเชื่อและตรวจสอบความถูกต้องของเหตุผล | - | ตรวจสอบความถูกต้องของเหตุผลในการปฏิเสธการให้สินเชื่อ |

### ตาราง Control/Evidence/Test

| Control | Evidence | Test | Sample Size | Risk Rating | Owner | Due Date | Remediation |
|---------|----------|------|-------------|-------------|-------|----------|-------------|
| ระบบบันทึกและรายงานผลการเข้าถึงข้อมูล | บันทึกการเข้าถึงข้อมูล (Log Files) | ตรวจสอบบันทึกการเข้าถึงข้อมูลและตรวจสอบความถูกต้อง | 100% | High | IT Security | 30/06/2024 | - |
| การตรวจสอบและแก้ไขข้อมูลของเจ้าของข้อมูล | บันทึกการตรวจสอบและแก้ไขข้อมูล | ตรวจสอบบันทึกการตรวจสอบและแก้ไขข้อมูลของเจ้าของข้อมูล | 100% | High | Data Governance | 30/06/2024 | - |
| การขอใช้ข้อมูลและความยินยอม | บันทึกการขอใช้ข้อมูลและความยินยอม | ตรวจสอบบันทึกการขอใช้ข้อมูลและตรวจสอบความยินยอมของเจ้าของข้อมูล | 100% | Medium | Compliance | 30/06/2024 | - |
| การปฏิเสธการให้สินเชื่อ | รายงานการปฏิเสธการให้สินเชื่อ | ตรวจสอบรายงานการปฏิเสธการให้สินเชื่อและตรวจสอบความถูกต้องของเหตุผล | 100% | High | Credit Risk | 30/06/2024 | - |

### Coverage Checklist

| มาตรา | ความครบถ้วนของหลักฐาน | Evidence Gap |
|--------|------------------------|--------------|
| มาตรา 17 | บันทึกการเข้าถึงข้อมูลและระบบการตรวจสอบ | - |
| มาตรา 19 | รายงานการส่งข้อมูลและความถูกต้องของข้อมูล | - |
| มาตรา 20 | บันทึกการขอใช้ข้อมูลและความยินยอม | - |
| มาตรา 25 | บันทึกการตรวจสอบและแก้ไขข้อมูล | - |
| มาตรา 26 | รายงานการตรวจสอบและแก้ไขข้อมูล | - |
| มาตรา 27 | บันทึกข้อโต้แย้งและหลักฐานประกอบ | - |
| มาตรา 28 | รายงานการปฏิเสธการให้สินเชื่อและความถูกต้องของเหตุผล | - |
