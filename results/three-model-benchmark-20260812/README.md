# ผลรายข้อ: 3 โมเดล × 3 datasets

ชุดนี้เก็บคำถาม, evidence ที่คัดเลือก, คำตอบ, citation, เวลา, metric หลัง inference และคะแนน blind language review ของทั้ง 15 ข้อครบถ้วน

- ไม่มี expected citation, reference answer หรือ raw prompt
- BF16 ใช้ frozen evidence ชุดเดียวกับ Q4/Qwen เพื่อวัดการสร้างคำตอบ ไม่ใช่ rerun retrieval
- ทุกผลเป็น preliminary / unreviewed และต้องให้ผู้เชี่ยวชาญกฎหมายไทยตรวจเมื่อนำไปใช้จริง

| Dataset | Case ID | Artifact |
|---|---|---|
| NitiBench | `nitibench-unlicensed-futures-market` | [JSON](cases/nitibench-unlicensed-futures-market.json) |
| NitiBench | `nitibench-orchard-lease` | [JSON](cases/nitibench-orchard-lease.json) |
| NitiBench | `nitibench-minor-adoption` | [JSON](cases/nitibench-minor-adoption.json) |
| NitiBench | `nitibench-current-account` | [JSON](cases/nitibench-current-account.json) |
| NitiBench | `nitibench-limited-company-shareholder` | [JSON](cases/nitibench-limited-company-shareholder.json) |
| พ.ร.บ. การประกอบธุรกิจข้อมูลเครดิต (NCB) | `ncb-owner-dispute` | [JSON](cases/ncb-owner-dispute.json) |
| พ.ร.บ. การประกอบธุรกิจข้อมูลเครดิต (NCB) | `ncb-disclosure-consent` | [JSON](cases/ncb-disclosure-consent.json) |
| พ.ร.บ. การประกอบธุรกิจข้อมูลเครดิต (NCB) | `ncb-correction-deadline` | [JSON](cases/ncb-correction-deadline.json) |
| พ.ร.บ. การประกอบธุรกิจข้อมูลเครดิต (NCB) | `ncb-rejection-reasons` | [JSON](cases/ncb-rejection-reasons.json) |
| พ.ร.บ. การประกอบธุรกิจข้อมูลเครดิต (NCB) | `ncb-unlawful-disclosure-penalty` | [JSON](cases/ncb-unlawful-disclosure-penalty.json) |
| BOT Digital Fraud Management | `bot-scope` | [JSON](cases/bot-scope.json) |
| BOT Digital Fraud Management | `bot-governance` | [JSON](cases/bot-governance.json) |
| BOT Digital Fraud Management | `bot-monitoring` | [JSON](cases/bot-monitoring.json) |
| BOT Digital Fraud Management | `bot-customer-response` | [JSON](cases/bot-customer-response.json) |
| BOT Digital Fraud Management | `bot-reporting` | [JSON](cases/bot-reporting.json) |
