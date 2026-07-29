# Live Open WebUI NCB structural-RAG benchmark

- Knowledge Base: `พ.ร.บ. การประกอบธุรกิจข้อมูลเครดิต (รวมแก้ไข 1-6)` (`7d2c3f84-181e-4dd4-a641-0a8b87902663`)
- Model: `iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b`
- vLLM context: 8,192 tokens; requested maximum answer: 1,024 tokens
- Retrieval: hybrid BM25 0.65 + Qwen3-Embedding-4B, top 8, BAAI/bge-reranker-v2-m3 top 3
- Mean retrieval time: 13.23s
- Mean end-to-end chat time: 48.49s
- Macro retrieval precision / recall: 46.7% / 63.3%

| Scenario | Expected | Retrieved | P | R | Prompt tokens | Output tokens | Retrieval | Chat |
|---|---|---|---:|---:|---:|---:|---:|---:|
| access-log-retention | 17 | 3, 17, 36 | 33% | 100% | 3989 | 1024 | 19.34s | 54.04s |
| data-correction-dispute | 25, 26, 27 | 27, 19, 26 | 67% | 67% | 2876 | 1024 | 7.61s | 43.74s |
| loan-broker-credit-model | 24/1, 24/2, 24/3 | 24/3, 3, 24/1 | 67% | 67% | 3850 | 1024 | 20.93s | 52.75s |
| adverse-credit-decision | 26, 27, 28 | 28, 24/4, 25 | 33% | 33% | 2583 | 1024 | 6.05s | 44.79s |
| unlawful-disclosure-liability | 20, 41 | 53, 51, 20 | 33% | 50% | 2797 | 1024 | 12.21s | 47.12s |

## access-log-retention

**Question:** ในฐานะ IT Internal Audit ของธนาคาร หากตรวจการเชื่อมต่อและการใช้งานข้อมูล NCB ควรตรวจ control และหลักฐาน access log อะไร และต้องเก็บบันทึกไว้นานเท่าใด

**Expected:** 17

**Retrieved:** 3, 17, 36

**Answer (54.04s, 1024 output tokens, 2,639 characters):**

We need to answer: As IT Internal Audit of a bank, if checking connections and usage of NCB data, what controls and evidence access logs should be checked, and how long to retain records. Must use only supplied context. The context includes definitions and sections 17, 36 of the Credit Information Business Act. Section 17 requires systems for processing data: system for categorizing data, correcting data, security, access logs, retention for at least 2 years. Section 36 gives powers of Bank of Thailand to investigate and request logs. However, the specific requirement for retention period is in Section 17 (7) "ระบบการทำลายข้อมูลที่มีอายุเกินกว่าที่คณะกรรมการกำหนด" but not specific period. Also Section 17 (6) requires recording and reporting access logs for at least 2 years. So answer: check controls: data categorization, data correction, security, access control, audit logs, retention. Evidence: access logs showing who accessed, when, what data, purpose. Retention: at least 2 years. Also mention that Bank of Thailand may request logs. Use citations: Section 17 (6) and (7) and Section 36. Provide answer in Thai, distinguishing legal requirement, audit evidence, evidence gap. Also note that if context insufficient, say so. But we have enough.
</think>
**สรุปข้อกำหนดตามพระราชบัญญัติการประกอบธุรกิจข้อมูลเครดิต พ.ศ. ๒๕๔๕**

| ประเด็น | ข้อกำหนดทางกฎหมาย | คำอธิบายสำหรับการตรวจสอบภายใน |
|--------|-------------------|--------------------------------|
| **ระบบการจัดทำและการเก็บรักษาข้อมูล** | มาตรา ๑๗ (๑) “ระบบจำแนกข้อมูลที่เก็บรักษาไว้” | ตรวจสอบว่า มีระบบหรือกระบวนการที่สามารถจำแนกข้อมูล NCB ตามประเภทและระดับความลับได้อย่างชัดเจน |
| **การแก้ไขข้อมูลให้ถูกต้อง** | มาตรา ๑๗ (๒) “ระบบการแก้ไขข้อมูลให้มีความถูกต้องสมบูรณ์และทันสมัยอยู่เสมอ” | ตรวจสอบกระบวนการตรวจสอบและยืนยันความถูกต้องของข้อมูลก่อนบันทึกและหลังการแก้ไข |
| **ความปลอดภัยและการควบคุมการเข้าถึง** | มาตรา ๑๗ (๓) “ระบบรักษาความลับและความปลอดภัยของข้อมูล” และ (๕) “ระบบการตรวจสอบและแก้ไขข้อมูลของเจ้าของข้อมูล” | ตรวจสอบมาตรการควบคุมการเข้าถึง (Access Control) เช่น การอนุญาตเฉพาะผู้ที่มีอำนาจ, การบันทึกการเข้าถึง (Access Log) และการป้องกันการแก้ไขข้อมูลโดยไม่ชอบ |
| **บันทึกการเข้าถึงข้อมูล** | มาตรา ๑๗ (๖) “ระบบบันทึกและรายงานผลทุกครั้งเมื่อมีผู้เข้าถึงข้อมูล โดยมีกำหนดระยะเวลาไม่น้อยกว่าสองปี” | ตรวจสอบให้มีระบบบันทึก (Log) ที่แสดงรายละเอียด: ผู้เข้าถึง, เวลา, จุดประสงค์, ข้อมูลที่เข้าถึง, ผลการตรวจสอบ. ต้องเก็บรักษาไม่น้อยกว่า 2 ปี เพื่อให้เจ้าของข้อมูลตรวจสอบได้ |
| **การทำลายข้อมูลเก่าที่หมดอายุ** | มาตรา ๑๗ (๗) “ระบบการทำลายข้อมูลที่มีอายุเกินกว่าที่คณะกรรมการกำหนด” | ตรวจสอบนโยบายการทำลายข้อมูลที่หมดอายุตามระยะเวลาที่คณะกรรมการกำหนด (

## data-correction-dispute

**Question:** ลูกค้าโต้แย้งว่าข้อมูลเครดิตไม่ถูกต้อง ธนาคารและบริษัทข้อมูลเครดิตต้องมีขั้นตอนตรวจสอบ แก้ไข แจ้งผล และบันทึกข้อโต้แย้งอย่างไร

**Expected:** 25, 26, 27

**Retrieved:** 27, 19, 26

**Answer (43.74s, 1024 output tokens, 3,728 characters):**

We need to answer in Thai, distinguishing legal requirement, audit evidence, and any evidence gap. Use only supplied context. The question: "ลูกค้าโต้แย้งว่าข้อมูลเครดิตไม่ถูกต้อง ธนาคารและบริษัทข้อมูลเครดิตต้องมีขั้นตอนตรวจสอบ แก้ไข แจ้งผล และบันทึกข้อโต้แย้งอย่างไร"

We need to cite sections: Section 27 (พ.ร.บ. การประกอบธุรกิจข้อมูลเครดิต) and Section 19 (same law). Also Section 26 maybe relevant for checking and correcting. But the question asks about steps: check, correct, inform, record dispute. Let's extract relevant parts.

Section 27: In case of dispute regarding correctness of data and cannot reach agreement, the credit bureau must record the dispute with supporting evidence of the data subject in the data subject's system. For preparing reports to serve members or users, the credit bureau must indicate in the report which data subjects have disputes. The data subject may appeal to the Committee for decision. If dispute arises between financial institution, member, or user and credit bureau or data subject and cannot reach agreement, the credit bureau must record the dispute in the data subject's system and inform relevant parties. The data subject may appeal to the Committee.

Section 19: Member duties: (4) If there is a dispute over data and cannot reach agreement, the member must report the dispute to the credit bureau to record as a dispute in the data subject's system. Also (3) If the data subject claims data is incorrect, the member must: (a) verify facts per request; (b) report results to credit bureau ASAP; (c) if data is incomplete or incorrect, correct and report correct data to all recipients; (d) consider correction request within 30 days; etc. Also (4) record dispute.

Section 26: When data subject exercises right to check or correct data, the credit bureau or member must consider request and verify data ASAP, and inform data subject of result and reasons within 30 days. If data is found incorrect, correct ASAP and inform relevant members/users to correct.

Thus steps: 1) Record dispute with supporting evidence in data subject's system. 2) Inform relevant parties (financial institution, member, user). 3) If dispute cannot be resolved, data subject may appeal to Committee. 4) Member must verify data, correct if needed, report to credit bureau, and record dispute. 5) Credit bureau must include dispute info in reports. 6) Both must act within timeframes (30 days for correction, 30 days for response). 7) Audit evidence: need supporting evidence from data subject, records of dispute, reports, committee decisions.

Now we need to distinguish legal requirement vs audit evidence vs evidence gap. The legal requirement is what law says. Audit evidence would be documents showing compliance: dispute records, correction logs, reports, committee decisions. Evidence gap: maybe missing supporting evidence or missing documentation of appeal.

We must answer in Thai, and include inline source markers [id] for statements directly supported by context. Use only supplied context. So we need to cite sections 27, 19, 26. Use [1] for Section 27, [2] for Section 19, [3] for Section 26.

We need to mention steps: record dispute, verify, correct, inform, report, appeal.

Let's craft answer:

- ขั้นตอนตรวจสอบ: เมื่อมีข้อโต้แย้งเกี่ยวกับความถูกต้องของข้อมูล ให้ธนาคารหรือบริษัทข้อมูลเครดิตตรวจสอบข้อมูลโดยเร็ว และแจ้งผลพร้อมเหตุผลให้เจ้าของข้อมูลทราบภายใน 30 วัน (อ้างมาตรา 26) หรือในกรณีที่เป็นสมาชิก ตรวจสอบตามมาตรา 19 (3) (ก) (ข)

- ขั้นตอนแก้ไข: หากพบว่าข้อมูลไม่ถูกต้อง ให้แก้ไขให้ถูกต้องโดยเร็ว และแจ้งให้สมาชิกหรือผู้ใช้บริการที่เกี่ยวข้องทราบเพื่อแก้ไขต่อไป (มาตรา 26) หรือสมาชิกต้องแก้ไขและรายงานข้อมูลที่ถูกต้องให้บริษัทข้อมูลเครดิตทราบทุกแห่งที่รับข้อมูลจากตน (มาต

## loan-broker-credit-model

**Question:** ธนาคารรับข้อมูลจากผู้ประกอบธุรกิจเป็นตัวกลางในการจัดหาสินเชื่อ และจะนำข้อมูลไปทำ credit model ต้องตรวจ consent, onward disclosure และการทำข้อมูลไม่ให้ระบุตัวบุคคลอย่างไร

**Expected:** 24/1, 24/2, 24/3

**Retrieved:** 24/3, 3, 24/1

**Answer (52.75s, 1024 output tokens, 2,880 characters):**

We need to answer in Thai, distinguishing legal requirement, audit evidence, and any evidence gap. Use only supplied context. The context includes sections 24/3, 24/1, and definitions. Need to explain that bank must obtain consent from data owner before using data for credit model, must ensure onward disclosure compliance, and must not identify individuals. Also need to cite sections.

From 24/3: Member may use data of customers, but must obtain consent from data owner. Use only for credit model for analysis and risk management. Also CMA may allow other members to use model with consent. Must follow criteria set by CMA. So legal requirement: consent, purpose limited, no identification, onward disclosure compliance.

From 24/1: Disclosure to members must have consent from data owner each time, unless consent given previously. Must follow CMA criteria.

Definitions: Data owner, data, etc.

Thus answer: Bank must verify consent, ensure data not identifying, limit use to credit model, ensure onward disclosure to other members follows consent, and comply with CMA regulations.

Audit evidence: Need proof of consent (signed forms), records of data usage, documentation of CMA criteria compliance, logs showing no personal identifiers, etc. Evidence gap: If no consent record, cannot use data; if model includes personal identifiers, gap.

Provide answer with sections.
</think>
**ข้อกฎหมายที่ต้องปฏิบัติตาม**

| ประเด็น | มาตราที่เกี่ยวข้อง | ข้อกำหนดตามกฎหมาย |
|--------|-------------------|----------------------|
| **การได้รับความยินยอมจากเจ้าของข้อมูล** | มาตรา ๒๔/๓ (วรรคหนึ่ง) และมาตรา ๒๔/๑ | ก่อนที่สมาชิกประเภทผู้ประกอบธุรกิจเป็นตัวกลางในการจัดหาสินเชื่อจะนำข้อมูลของลูกค้าไปใช้เป็นปัจจัยในการจัดทำแบบจำลองด้านเครดิต ต้องได้รับความยินยอมจากเจ้าของข้อมูลทุกครั้ง (เว้นแต่เจ้าของข้อมูลได้ให้ความยินยอมไว้เป็นอย่างอื่น) |
| **การใช้ข้อมูลเฉพาะเพื่อประโยชน์ในการวิเคราะห์สินเชื่อและการบริหารความเสี่ยง** | มาตรา ๒๔/๓ (วรรคหนึ่ง) | ข้อมูลที่นำไปใช้ในการจัดทำแบบจำลองด้านเครดิตต้องใช้เฉพาะเพื่อประโยชน์ในการวิเคราะห์สินเชื่อแทนผู้ที่จะให้สินเชื่อและการบริหารความเสี่ยงของสมาชิกเท่านั้น |
| **การอนุญาตให้สมาชิกอื่นนำแบบจำลองไปใช้** | มาตรา ๒๔/๓ (วรรคสอง) | คณะกรรมการอาจอนุญาตให้สมาชิกอื่นนำแบบจำลองด้านเครดิตไปใช้เฉพาะเพื่อประโยชน์ในการวิเคราะห์สินเชื่อ การออกบัตรเครดิตและการบริหารความเสี่ยงของสมาชิกอื่นได้ โดยต้องปฏิบัติตามหลักเกณฑ์ วิธีการ และเงื่อนไขที่คณะกรรมการประกาศกำหนด |
| **การตรวจสอบความถูกต้องของการให้ความยินยอมและการปฏิบัติตามเงื่อนไข** | มาตรา ๒๔/๑ | การเปิดเผยหรือให้ข้อมูลแก่สมาชิกต้องได้รับความยินยอมจากเจ้าของข้อมูลก่อนทุกครั้ง และต้องปฏิบัติตามหลักเกณฑ์ วิธีการ และเงื่อนไขที่คณะกรรมการประกาศกำหนด |

**สรุปข้อกำหนดหลัก**

1. **Consent (ความยินยอม)** – ธนาคารต้องตรวจสอบว่ามีการได้รับความยินยอมจากเจ้าของข้อมูล (ลูกค้า) อย่างชัดเจนและบันทึกไว้เป็นหลักฐานก่อนใช้ข้อมูลใด ๆ ในการทำ credit model
2. **Onward Disclosure (การเปิดเผยต่อไป)** – หาก

## adverse-credit-decision

**Question:** เมื่อธนาคารปฏิเสธสินเชื่อเพราะข้อมูล NCB ต้องแจ้งลูกค้าอย่างไร ลูกค้ามีสิทธิตรวจสอบหรือขอให้พิจารณาใหม่อย่างไร

**Expected:** 26, 27, 28

**Retrieved:** 28, 24/4, 25

**Answer (44.79s, 1024 output tokens, 2,805 characters):**

We need to answer in Thai, distinguishing legal requirement, audit evidence, and any evidence gap. Use only supplied context. The question: When a bank denies a loan because of NCB data, what must be notified to the customer, and what rights does the customer have to check or request reconsideration?

From context: Section 28 (and 24/4) says: In case of denial of loan or other actions causing higher fees due to data, the financial institution must show reasons for denial, including source of data, in writing to the customer. The customer has the right to check the accuracy of their data without fee, within 30 days of denial. If they believe data is incorrect, they can request reconsideration with supporting evidence. Also Section 25 lists rights: right to know what data is held, right to check data, right to correct inaccurate data, right to contest when data is inaccurate, right to be informed of results within specified time, right to be informed of reasons for denial, right to appeal to committee.

Thus answer: Bank must notify in writing the reasons for denial and source of data. Customer can check data within 30 days, no fee. If data is wrong, can request reconsideration with evidence. Also can appeal to committee.

Need to cite sections: Section 28, Section 24/4, Section 25. Use inline source markers.

We must distinguish legal requirement (what law says) vs audit evidence (maybe not needed). The context is law, not audit evidence. So we can state legal requirement. No evidence gap.

Answer in Thai, include citations.
</think>
ธนาคาร (สถาบันการเงิน) ต้องแจ้งลูกค้าเป็นหนังสือทั้งเหตุผลที่ปฏิเสธการให้สินเชื่อและแหล่งที่มาของข้อมูลที่ใช้เป็นเหตุแห่งการปฏิเสธนั้น ตามมาตรา 28 แห่งพระราชบัญญัติการประกอบธุรกิจข้อมูลเครดิต พ.ศ. ๒๕๔๕ (และมาตรา 24/4 สำหรับสมาชิกประเภทผู้ประกอบธุรกิจเป็นตัวกลางในการจัดหาสินเชื่อ)

ลูกค้ามีสิทธิดังต่อไปนี้

1. **ตรวจสอบความถูกต้องของข้อมูล** – มีสิทธิตรวจสอบข้อมูลของตนโดยไม่ต้องเสียค่าธรรมเนียม ภายในสามสิบวันนับแต่วันที่ได้รับคำปฏิเสธการขอสินเชื่อหรือการดำเนินการอื่นใดที่ก่อให้เกิดการขึ้นค่าบริการ (มาตรา 28)

2. **ขอให้พิจารณาใหม่** – หากเห็นว่าข้อมูลไม่ถูกต้อง สามารถยื่นคำขอพร้อมแสดงหลักฐานประกอบเพื่อให้สถาบันการเงินหรือสมาชิกพิจารณาประกอบการให้สินเชื่อหรือการดำเนินการอื่น ๆ อีกครั้งหนึ่งได้ (มาตรา 28)

3. **ได้รับแจ้งผลการตรวจสอบ** – มีสิทธิได้รับแจ้งผลการตรวจสอบข้อมูลของตนภายในระยะเวลาที่กำหนด (มาตรา 25)

4. **อุทธรณ์ต่อคณะกรรมการ** – ในกรณีที่ยังไม่พอใจผลการพิจารณา สามารถอุทธรณ์ต่อคณะกรรมการตามมาตรา 27 ได้ (มาตรา 25)

ดังนั้น ธนาคารต้องแจ้งเหตุผลและแหล่งที่มาของข้อมูลในหนังสือให้ลูกค้าทราบ และลูกค้ามีสิทธิตรวจสอบข้อมูลโดยไม่เสียค่าใช้จ่ายภายใน 30 วัน และสามารถขอให้พิจารณาใหม่โดยยื่นคำขอพร้อมหลักฐานประกอบได้.

[1] พระราชบัญญัติการประกอบธุรกิจข้อมูลเครดิต พ.ศ. ๒๕๔๕ มาตรา 28
[2] พระราชบัญญัติการประกอบธุรกิจข้อม

## unlawful-disclosure-liability

**Question:** ถ้าพนักงานธนาคารเปิดเผยข้อมูลเครดิตแก่บุคคลที่ไม่มีสิทธิ ให้วิเคราะห์ข้อกำหนดการเปิดเผย ความรับผิดทางแพ่ง และหลักฐานที่ผู้ตรวจสอบควรรวบรวม

**Expected:** 20, 41

**Retrieved:** 53, 51, 20

**Answer (47.12s, 1024 output tokens, 3,954 characters):**

We need to answer: "ถ้าพนักงานธนาคารเปิดเผยข้อมูลเครดิตแก่บุคคลที่ไม่มีสิทธิ ให้วิเคราะห์ข้อกำหนดการเปิดเผย ความรับผิดทางแพ่ง และหลักฐานที่ผู้ตรวจสอบควรรวบรวม"

We must use only supplied context. The context includes sections 20, 51, 53. Section 20 defines when a credit bureau may disclose info without consent, including to members, etc., and to certain authorities. Section 51 penalizes a credit bureau or data processor disclosing info beyond what is allowed in sections 20 or 24/1. Section 53 penalizes individuals (including directors) who disclose info they know, unless exceptions.

Thus, if a bank employee discloses credit info to a person without right, that is a violation of Section 20 (if not allowed) and Section 51 (if it's the bureau or processor). Also Section 53 applies to individuals (including employees) who disclose info they know, unless exceptions (e.g., for investigation, legal proceedings, etc.). So we need to analyze: what are the disclosure rules? Under Section 20, disclosure without consent is allowed only in specific cases: (1) court order, (2) police request for criminal investigation, (3) request from Ministry of Finance, Bank of Thailand, SEC, etc., (4) request from BTS (Land Development?), (5) request from BTS (maybe typo) for asset securitization, (6) request from BTS (maybe BTS) for asset management, (7) request from other entities for public litigation.

If the disclosure is not covered by these exceptions, it's a violation. The employee's liability: under Section 53, any person who discloses info they know, unless exceptions, is punishable. Also Section 51 imposes penalties on the credit bureau or data processor for disclosing beyond Section 20/24/1.

Civil liability: The data subject may claim damages for breach of confidentiality and violation of rights. The law does not explicitly state civil liability but the penalties indicate strict liability; civil suit can be based on tort.

Evidence for auditor: Need to collect documents: (1) the credit report or data disclosed; (2) the request or authority that purportedly justified disclosure (e.g., court order, police letter, ministry letter); (3) internal memos or instructions from the bank authorizing disclosure; (4) the employee's statement or testimony; (5) any consent from data owner (if any); (6) the relevant sections of the Act (20, 51, 53) as legal basis; (7) any breach of internal policy.

Thus answer in Thai, distinguishing legal requirement, audit evidence, and evidence gaps. Cite sections.

We must cite exact law name and bare section number. Use [id] for source that directly supports each statement. For legal requirement, we cite Section 20, 51, 53. For evidence gap, we note that the context does not specify civil liability details, so we state that.

Let's craft answer:

- Legal requirement: Under Section 20, disclosure without consent is only permitted in specific cases; if not, it's prohibited. Under Section 51, the credit bureau/processor must not disclose beyond Section 20/24/1; violation leads to criminal penalty. Under Section 53, any person (including employee) who discloses info they know, unless exceptions, is punishable.

- Civil liability: Not explicitly in the provided sections; thus we cannot conclude civil liability from the text, but the breach may give rise to civil claims under general law.

- Evidence: Need to collect the specific disclosure document, the authority (court order, police letter, etc.), internal approval, and the employee's record. Also need to verify that the disclosure falls outside the exceptions in Section 20.

Add source markers: Section 20 from source id=3, Section 51 from id=2, Section 53 from id=1.

Now produce final answer.
</think>
**ข้อกำหนดการเปิดเผยตามกฎหมาย**
- ตาม **มาตรา ๒๐** แห่งพระราชบัญญัติการประกอบธุรกิจข้อมูลเครดิต พ.ศ. ๒๕๔๕ การเปิดเผยข้อมูลเครดิตโดยไม่ได้รับความยินยอมจากเจ้าของข้อมูลต้องเป็นไปตามกรณีที่กฎหมายกำหนดไว้โดยเฉพาะ ได้แก่ (๑) มีคำ
