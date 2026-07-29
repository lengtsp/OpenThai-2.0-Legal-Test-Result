# OpenThai 2.0 Legal vs Qwen3.6-27B

วันที่ทดสอบ: 29 กรกฎาคม 2026

การทดสอบนี้เปรียบเทียบ **generation/selection** โดยใช้ final evidence
packet เดียวกัน ไม่ได้นำคะแนน retrieval ของโมเดลหนึ่งไปเทียบกับอีกโมเดล

โมเดล:

- OpenThai:
  [`iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b`](https://huggingface.co/iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b)
  ผ่าน vLLM
- Qwen: `Qwen3.6-27B-UD-Q8_K_XL.gguf` ผ่าน llama.cpp

ผู้จัดทำเป็นผู้ทดสอบอิสระ ไม่ใช่ผู้พัฒนาหรือผู้รับรองทั้งสองโมเดล
ผลนี้ไม่ใช่คำแนะนำทางกฎหมาย

## สภาพแวดล้อม Qwen

| Item | Value |
|---|---|
| API | OpenAI-compatible, `127.0.0.1:8081` |
| Context | 12,032 runtime tokens |
| Reasoning | off |
| GPU | NVIDIA RTX PRO 6000 Blackwell Workstation Edition |
| VRAM หลังโหลดพร้อม embedding | ประมาณ 39.4 GB |
| Startup time | 4 นาที 54 วินาที |
| Quantization/file | UD-Q8_K_XL, ประมาณ 33 GB |

OpenThai ถูก unload หลังจบและอัปโหลดผล OpenThai แล้วจึงเริ่ม Qwen
เพื่อไม่ให้ VRAM ไม่พอ ส่วน embedding service อยู่ใน GPU ตลอดการทดสอบ

## วิธีควบคุมความยุติธรรม

1. NitiBench ใช้คำถาม, expected section และ supplied top-10 chunks ชุดเดียวกัน
2. NCB ใช้ structural chunks และลำดับ evidence ที่บันทึกจาก OpenThai run
3. Citation ใช้ `temperature=0.0`, `top_p=1.0`, `max_tokens=2,048`
4. Essay ใช้ `temperature=0.7`, `top_p=0.9`, `max_tokens=4,096`
5. General legal chat ใช้ `temperature=0.7`, `top_p=0.9`, `max_tokens=2,048`
6. ปิด thinking/reasoning ทั้งสองโมเดลในรอบเทียบหลัก

Qwen ไม่ได้ใช้ OpenThai เป็น reranker ในรอบนี้ เพราะต้องการวัด generator
บน evidence เดียวกันโดยตรง

## สรุปผล

| Test | OpenThai | Qwen3.6-27B | ข้อสรุป |
|---|---:|---:|---|
| NitiBench echo exact | 9/9 | 9/9 | เท่ากัน |
| NitiBench selection exact แบบ structured pipeline | 5/9 | **6/9** | Qwen สูงกว่า 1 case |
| NitiBench selection macro recall | 66.67% | **77.78%** | Qwen สูงกว่า |
| NitiBench selection macro precision | 61.11% | **72.22%** | Qwenสูงกว่า |
| NCB focused exact | 5/5 | 5/5 | เท่ากัน |
| Closed-book strict | 0/5 | **1/5** | ทั้งคู่ยังไม่เหมาะกับเลขมาตรา |
| Essay section anchors | 2/2 | 2/2 | เท่ากัน แต่ substantive errors ต่างกัน |
| Legal chat continuity | 3/3 | 3/3 | เท่ากัน |

Qwen selection มี JSON ถูก 8/9 ส่วน OpenThai 9/9 กรณีภาษีของ Qwen
มี citation มาตรา 81 ในเนื้อหา แต่ JSON invalid เพราะมีเครื่องหมายคำพูด
ที่ไม่ escape จึงถูกนับเป็น pipeline failure หากซ่อม JSON เพื่ออ่านเชิง
semantic อย่างเดียว Qwen จะอ้าง expected section ครบ 8/9, exact citation
set 7/9, macro recall 88.89% และ macro precision 83.33% แต่ตัวเลขนี้
ไม่ใช่คะแนน production structured output

## NitiBench open-book selection

| Case | Expected | OpenThai | Qwen | วิเคราะห์ |
|---|---|---|---|---|
| Guardian consent | 1598/5 | ผ่าน | ผ่าน | ทั้งคู่เลือกได้ |
| Digital token offer | 62 | 22 | 22, 19 | ทั้งคู่เลือก near-miss |
| Foreign business shareholding | 13 | 15 | 15, 13 | Qwen พบมาตราถูกแต่เพิ่มเกิน |
| Liquidator fraud | กฎหมายความผิดนิติบุคคล 38 | บริษัทมหาชน 214 | ผ่าน | Qwen แยกกฎหมายได้ดีกว่าในเคสนี้ |
| Financial institution fraud | 146 | ผ่าน | ผ่าน | ทั้งคู่เลือกได้ |
| Public company email | 7/1 | ผ่าน | ผ่าน | ทั้งคู่เลือกได้ |
| Unlicensed futures exchange | 132 | ผ่าน | ผ่าน | ทั้งคู่เลือกได้ |
| Future asset security | 9 | ผ่าน | ผ่าน | ทั้งคู่เลือกได้ |
| Tax animal-feed import | 81 | 81 + 79/2 | 81 แต่ JSON invalid | OpenThai schema ดีกว่า; ทั้งคู่ต้องตรวจข้อสรุปภาษี |

## NCB focused RAG

เมื่อส่ง packet ที่มีเฉพาะมาตราที่ใช้จริง:

| Scenario | Evidence | OpenThai | Qwen |
|---|---|---:|---:|
| Employee data leak | 24, 54 | ผ่าน | ผ่าน |
| Cross-selling | 20, 22 | ผ่าน | ผ่าน |
| Adverse decision/dispute | 28, 27, 26 | ผ่าน | ผ่าน |
| Data lifecycle | 10, 12, 13 | ผ่าน | ผ่าน |
| Licence/exclusivity | 6, 9 | ผ่าน | ผ่าน |

ครั้งแรก Qwen ได้ adverse-decision 2/3 เมื่อเรียง 26→27→28 แต่เมื่อใช้
ลำดับเดียวกับ OpenThai 28→27→26 ได้ 3/3 จึงบันทึกเป็น
**positional sensitivity** ไม่ใช้ผลรอบแรกในคะแนนสุดท้าย

ข้อสรุปสำหรับ RAG: นอกจากเลือก chunk ถูกแล้ว ควรจัดกลุ่ม/เรียงหลักฐาน
ตามประเด็นของคำถามและตรวจ coverage หลัง generation

## Closed-book

| Scenario | OpenThai | Qwen | Strict verdict |
|---|---|---|---|
| แบบรายงานหลักทรัพย์เท็จ | 264, 265 | 233, 265, 269 | ทั้งคู่ไม่ผ่าน |
| ส่งออกกัญชาไม่มีใบอนุญาต | 102 | 29, 30, 31, 59 | ทั้งคู่ไม่ผ่าน |
| บุคคลต้องห้ามเข้าเมือง | 12 | 12 | ไม่ครบ (7)/(8) |
| ข้อมูลสุขภาพ PDPA | 24 | **26** | Qwen ผ่าน |
| ร้านอาหาร/สถานบริการ evidence gap | เดามาตรา 108 | เดามาตรา 3 | ทั้งคู่ไม่ abstain |

แม้ Qwen สูงกว่า 1/5 แต่ยังไม่เพียงพอสำหรับงาน production ที่ต้องการ
เลขมาตรา exact ทั้งสองโมเดลต้องใช้ retrieval และ primary-law validation

## Legal essay

| Model | Section anchors | Mean time | Completion tokens |
|---|---:|---:|---:|
| OpenThai thinking off | 2/2 | 41.68 s | 2,281 |
| Qwen reasoning off | 2/2 | **30.53 s** | 2,454 |

### SEC/Bitkub

- OpenThai อ้าง 76, 88(2), 94 ครบ แต่สับสนหน่วยงาน/ลำดับหลังกล่าวโทษ
  และเพิ่ม ป.ป.ช. ที่โจทย์ไม่ได้ระบุ
- Qwen อธิบายสถานะกล่าวโทษ→สอบสวน→อัยการ→ศาลได้ดีกว่า แต่สลับบทบาท
  ของมาตรา 88(2) และ 94 เมื่ออธิบายสาระของตัวบท
- ทั้งคู่แสดงว่า “มีเลขมาตราครบ” ไม่เท่ากับ “อธิบายมาตราถูก”

### NCB employee leak

- ทั้งคู่อ้างมาตรา 24 และ 54 รวมถึงโทษได้ตรง evidence
- Qwen ให้แนวทาง log, UBA, DRM, access review และ evidence preservation
  ครบกว่า
- Qwen overclaim ว่าธนาคารอาจต้องรับผิดเพราะพิสูจน์ controls ไม่ได้ ทั้งที่
  evidence packet สองมาตราไม่เพียงพอรองรับข้อสรุปดังกล่าว
- OpenThai เสนอ remediation ซ้ำและ coverage ด้าน control แคบกว่า

Codex judge จึงไม่ประกาศผู้ชนะ essay: Qwen เด่นด้านโครงงาน audit,
OpenThai กระชับกว่า แต่ทั้งสองต้องตรวจ legal substance โดยมนุษย์

## General legal chat

| Model | 3-turn continuity | Mean time | Completion tokens |
|---|---:|---:|---:|
| OpenThai | ผ่าน | 24.73 s | 1,769 |
| Qwen | ผ่าน | **24.07 s** | 2,855 |

- OpenThai ยึดมาตรา 20 มากกว่า แต่ตีความ exception workflow ปนกับ
  consent checklist
- Qwen ให้ audit checklist ใช้งานได้มากกว่า แต่เติม PDPA, active opt-in,
  withdrawal และ assertion ว่าข้อมูลเครดิตเป็น sensitive data โดยไม่มี
  evidence ใน packet
- Qwen verbose กว่า 61% จาก completion tokens รวม

ใช้ทั้งสองเป็น draft assistant ได้ แต่ UI ควรแสดง evidence และแยกข้อความ
ที่ “มาจากกฎหมาย” ออกจาก “แนวปฏิบัติที่โมเดลเสนอ”

## Latency

| Group | OpenThai mean | Qwen mean |
|---|---:|---:|
| NitiBench echo | **5.15 s** | 6.28 s |
| NitiBench selection | 5.97 s | **5.75 s** |
| NCB focused | 15.75 s | **13.05 s** |
| Closed-book | **5.42 s** | 6.35 s |
| Legal essay | 41.68 s | **30.53 s** |
| General legal chat | 24.73 s | **24.07 s** |

เวลานี้เปรียบเทียบ serving stacks และ quantization คนละชนิดด้วย
ไม่ใช่ benchmark สถาปัตยกรรมแบบ apples-to-apples

## คำแนะนำเลือกใช้

OpenThai เหมาะเมื่อ:

- ต้องการ JSON citation contract ที่เสถียรกว่าในชุดนี้
- งานหลักเป็น Thai statutory citation และใช้ prompt ตาม model card
- ใช้ focused RAG พร้อม validator

Qwen เหมาะเมื่อ:

- ต้องการ drafting/checklist ที่ครอบคลุมกว่า
- ยอมรับการใช้ JSON repair/validator และควบคุม verbosity
- ต้องใช้ general-purpose reasoning ร่วมกับงานกฎหมาย

ไม่ว่าเลือกโมเดลใด:

1. Structural chunk หนึ่งมาตราต่อหนึ่งชิ้น
2. Candidate 20–32 จาก dense + BM25 + FTS
3. Rerank แล้วลดเหลือ evidence 2–6 ชิ้น
4. เรียง evidence ตาม issue และตรวจ section coverage
5. Reject/repair JSON ที่ parse ไม่ได้
6. ตรวจทุก citation ว่าอยู่ใน context
7. เปิด primary source และให้ Legal/Compliance ลงนามข้อสรุป

## ไฟล์

- [Qwen raw results](../../results/qwen27-controlled-comparison-20260729/results.json)
- [Benchmark script](../../tools/advanced_rag/benchmark_qwen27_controlled_generation.py)
- [OpenThai advanced RAG report](../advanced-hybrid-rag-20260729/)
