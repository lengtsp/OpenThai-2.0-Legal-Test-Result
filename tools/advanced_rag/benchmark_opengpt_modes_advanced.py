#!/usr/bin/env python3
"""End-to-end benchmark for the four generation modes exposed on port 8083."""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


CITATION_CASES = [
    {
        "id": "employee-leak",
        "question": "พนักงานธนาคารแคปรายงานข้อมูลเครดิตของลูกค้าที่เป็นบุคคลมีชื่อเสียงส่งเข้า Line กลุ่มเพื่อน ต้องพิจารณาหน้าที่และโทษตามมาตราใด",
        "expected": ["24", "54"],
    },
    {
        "id": "cross-selling",
        "question": "ธนาคารนำข้อมูลเครดิตที่ขอเพื่อวิเคราะห์สินเชื่อบ้านไปให้บริษัทประกันในเครือทำ cross-selling ได้หรือไม่",
        "expected": ["20", "22"],
    },
    {
        "id": "adverse-decision",
        "question": "ธนาคารปฏิเสธสินเชื่อโดยอ้างข้อมูลเครดิต ต้องแจ้งอะไร และหากข้อมูลยังโต้แย้งกันอยู่ลูกค้ามีขั้นตอนใดต่อ",
        "expected": ["26", "27", "28"],
    },
    {
        "id": "data-lifecycle",
        "question": "พบการกระทำ 3 ข้อแยกกัน: (1) ผู้ประมวลผลจัดเก็บ “ข้อมูลห้ามจัดเก็บ” (2) ประมวลผลข้อมูลภายนอกราชอาณาจักร และ (3) ประมวลผลข้อมูลที่มีอายุเกินกำหนด จงวินิจฉัยและอ้างมาตราสำหรับแต่ละข้อ",
        "expected": ["10", "12", "13"],
    },
    {
        "id": "license-exclusivity",
        "question": "กลุ่มธนาคารจะตั้งบริษัทประกอบธุรกิจข้อมูลเครดิต ต้องขออนุญาตอย่างไร และบุคคลอื่นที่ไม่ใช่บริษัทข้อมูลเครดิตทำธุรกิจนี้ได้หรือไม่",
        "expected": ["6", "9"],
    },
]

CLOSED_BOOK_CASES = [
    {
        "id": "sec-false-filing",
        "question": "ผู้รายงานยื่นแบบ 59 และแบบ 246-2 ต่อ ก.ล.ต. เป็นเท็จทั้งที่ไม่มีการถือหรือจำหน่ายหลักทรัพย์ตามรายงาน ควรพิจารณามาตราใด และต้องระวังสถานะคดีอย่างไร",
        "expected": ["302/1"],
        "note": "source-reported assertion; primary-law verification required",
    },
    {
        "id": "controlled-herb-export",
        "question": "ผู้ประกอบการจำหน่าย แปรรูป และส่งออกช่อดอกกัญชาเพื่อการค้าโดยไม่มีใบอนุญาต ควรพิจารณากฎหมายและมาตราใด",
        "expected": ["46", "78"],
        "note": "source-reported assertion; primary-law verification required",
    },
    {
        "id": "immigration-prohibited-person",
        "question": "คนต่างด้าวที่มีพฤติการณ์เป็นภัยต่อสังคมหรือมีหมายจับต่างประเทศอาจเป็นบุคคลต้องห้ามตามมาตราใดของ พ.ร.บ.คนเข้าเมือง",
        "expected": ["12(7)", "12(8)"],
        "note": "source-reported assertion; primary-law verification required",
    },
    {
        "id": "pdpa-health-data",
        "question": "เวชระเบียนและข้อมูลสุขภาพเป็นข้อมูลส่วนบุคคลประเภทใดตาม พ.ร.บ.คุ้มครองข้อมูลส่วนบุคคล และมาตราใดเกี่ยวข้อง",
        "expected": ["26"],
        "note": "source-reported assertion; primary-law verification required",
    },
    {
        "id": "venue-evidence-gap",
        "question": "ร้านจดเป็นร้านอาหารแต่มีดนตรี ขายสุรา และมีการเต้นรำ เข้าข่ายสถานบริการตามมาตราใด ขอให้ตอบเฉพาะเมื่อมั่นใจและบอกข้อจำกัดของข้อมูล",
        "expected": [],
        "note": "the source scenario did not identify a section; hallucination-control case",
    },
]

ESSAY_CASES = [
    {
        "id": "sec-bitkub-false-report",
        "use_rag": False,
        "expected": ["76", "88(2)", "94"],
        "question": """เขียนบทวิเคราะห์กฎหมายแบบ legal essay จากข้อเท็จจริงต่อไปนี้ โดยแยก (1) การกระทำของบริษัท
(2) ความรับผิดของกรรมการ (3) การลงข้อความเท็จในเอกสารนิติบุคคล และ (4) สถานะของการกล่าวโทษ:
ศูนย์ซื้อขายสินทรัพย์ดิจิทัลถูกโจรกรรมสินทรัพย์ลูกค้า แต่แบบรายงานเงินกองทุนสภาพคล่องสุทธิรายวัน
ที่ส่ง ก.ล.ต. ไม่สะท้อนความเสียหาย กรรมการสองคนรับผิดชอบการนำส่งและลงข้อความในรายงานดังกล่าว
ก.ล.ต. ระบุ พ.ร.ก.สินทรัพย์ดิจิทัลฯ มาตรา 76 มาตรา 94 และมาตรา 88(2)
ปัจจุบันเป็นเพียงขั้นกล่าวโทษต่อ บก.ปอศ. ยังต้องผ่านการสอบสวน อัยการ และศาล""",
    },
    {
        "id": "ncb-audit-data-leak",
        "use_rag": True,
        "expected": ["24", "54"],
        "question": """ในฐานะ IT Internal Audit ของธนาคาร เขียน legal essay วิเคราะห์กรณีพนักงานสินเชื่อเปิดดู
รายงานข้อมูลเครดิตของลูกค้าที่ไม่มีความเกี่ยวข้องกับงาน แล้วแคปหน้าจอส่งในกลุ่ม Line ส่วนตัว
ให้แยกองค์ประกอบหน้าที่รักษาความลับ ผลทางกฎหมาย หลักฐานดิจิทัลที่ควรเก็บ และ control remediation
โดยอ้างเฉพาะมาตราที่มีหลักฐานในคลัง""",
    },
]

CHAT_TURNS = [
    "ช่วยอธิบายแบบภาษาคนทั่วไปว่า ทำไมธนาคารต้องขอความยินยอมก่อนดึงข้อมูลเครดิต",
    "ถ้าฉันเป็น IT Auditor ควรขอดูหลักฐานอะไรเพื่อยืนยันว่าความยินยอมนั้นใช้ได้จริง",
    "สรุปจากสองคำตอบก่อนหน้าเป็น checklist 5 ข้อ และบอกด้วยว่าประเด็นใดต้องให้ฝ่ายกฎหมายตรวจต่อ",
]


def normalize_section(value: object) -> str:
    return re.sub(r"^มาตรา\s*", "", str(value or "").strip()).translate(
        str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
    )


def sections_in_text(text: str) -> set[str]:
    normalized = text.translate(str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789"))
    return set(re.findall(r"มาตรา\s*([0-9]+(?:/[0-9]+)?(?:\([0-9]+\))?)", normalized))


def post(endpoint: str, payload: dict) -> dict:
    started = time.perf_counter()
    response = requests.post(endpoint, json=payload, timeout=1800)
    response.raise_for_status()
    body = response.json()
    body["wall_seconds"] = round(time.perf_counter() - started, 2)
    return body


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:8083/api/chat")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--groups", default="citation,closed_book,essay,chat")
    parser.add_argument("--case-ids", default="", help="Optional comma-separated case IDs for a partial rerun")
    parser.add_argument("--essay-mode", choices=("legal_essay", "legal_essay_thinking"), default="legal_essay")
    args = parser.parse_args()
    requested = set(args.groups.split(","))
    requested_cases = {value for value in args.case_ids.split(",") if value}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    output = json.loads(args.out.read_text(encoding="utf-8")) if args.out.exists() else {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "endpoint": args.endpoint,
        "complete": False,
        "groups": {},
    }
    output["complete"] = False

    def checkpoint() -> None:
        args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    if "citation" in requested:
        rows = list(output["groups"].get("citation_rag", []))
        selected_cases = [case for case in CITATION_CASES if not requested_cases or case["id"] in requested_cases]
        replacing = {case["id"] for case in selected_cases}
        rows = [row for row in rows if row.get("case", {}).get("id") not in replacing]
        for case in selected_cases:
            body = post(args.endpoint, {
                "mode": "citation_rag", "question": case["question"], "use_rag": True, "top_k": 10,
            })
            cited = {normalize_section(item.get("section")) for item in body.get("model_citations", [])}
            expected = set(case["expected"])
            rows.append({
                "case": case, "answer": body.get("answer"), "model_citations": sorted(cited),
                "evidence_sections": [normalize_section(item.get("section", "").split(" ·", 1)[0]) for item in body.get("citations", [])],
                "citation_recall": round(len(cited & expected) / len(expected), 4),
                "citation_precision": round(len(cited & expected) / max(1, len(cited)), 4),
                "retrieval": body.get("retrieval"), "usage": body.get("usage"),
                "timing": body.get("timing"), "wall_seconds": body["wall_seconds"],
            })
            output["groups"]["citation_rag"] = rows
            checkpoint()
            print("citation", case["id"], sorted(cited), flush=True)

    if "closed_book" in requested:
        rows = list(output["groups"].get("closed_book", []))
        selected_cases = [case for case in CLOSED_BOOK_CASES if not requested_cases or case["id"] in requested_cases]
        replacing = {case["id"] for case in selected_cases}
        rows = [row for row in rows if row.get("case", {}).get("id") not in replacing]
        for case in selected_cases:
            body = post(args.endpoint, {
                "mode": "closed_book", "question": case["question"], "use_rag": False,
            })
            cited = sections_in_text(body.get("answer", ""))
            expected = set(case["expected"])
            rows.append({
                "case": case, "answer": body.get("answer"), "sections_in_answer": sorted(cited),
                "expected_found": sorted(cited & expected),
                "expected_recall": round(len(cited & expected) / len(expected), 4) if expected else None,
                "evidence_gap_pass": not cited if not expected else None,
                "usage": body.get("usage"), "timing": body.get("timing"), "wall_seconds": body["wall_seconds"],
            })
            output["groups"]["closed_book"] = rows
            checkpoint()
            print("closed_book", case["id"], sorted(cited), flush=True)

    if "essay" in requested:
        rows = list(output["groups"].get(args.essay_mode, []))
        selected_cases = [case for case in ESSAY_CASES if not requested_cases or case["id"] in requested_cases]
        replacing = {case["id"] for case in selected_cases}
        rows = [row for row in rows if row.get("case", {}).get("id") not in replacing]
        for case in selected_cases:
            body = post(args.endpoint, {
                "mode": args.essay_mode, "question": case["question"], "use_rag": case["use_rag"], "top_k": 10,
            })
            cited = sections_in_text(body.get("answer", ""))
            expected = set(case["expected"])
            rows.append({
                "case": case, "answer": body.get("answer"), "reasoning": body.get("reasoning"),
                "sections_in_answer": sorted(cited), "expected_found": sorted(cited & expected),
                "expected_recall": round(len(cited & expected) / len(expected), 4),
                "evidence_sections": [normalize_section(item.get("section", "").split(" ·", 1)[0]) for item in body.get("citations", [])],
                "usage": body.get("usage"), "timing": body.get("timing"), "finish_reason": body.get("finish_reason"),
                "wall_seconds": body["wall_seconds"],
            })
            output["groups"][args.essay_mode] = rows
            checkpoint()
            print("essay", case["id"], sorted(cited), flush=True)

    if "chat" in requested:
        rows = []
        session_id = None
        for turn, question in enumerate(CHAT_TURNS, start=1):
            body = post(args.endpoint, {
                "mode": "general_legal_chat", "question": question, "use_rag": True,
                "top_k": 6, "session_id": session_id,
            })
            session_id = body["session"]["id"]
            rows.append({
                "turn": turn, "question": question, "answer": body.get("answer"),
                "session_id": session_id,
                "evidence_sections": [normalize_section(item.get("section", "").split(" ·", 1)[0]) for item in body.get("citations", [])],
                "usage": body.get("usage"), "timing": body.get("timing"), "wall_seconds": body["wall_seconds"],
            })
            output["groups"]["general_legal_chat"] = rows
            checkpoint()
            print("chat", turn, session_id, flush=True)

    output["complete"] = True
    checkpoint()


if __name__ == "__main__":
    main()
