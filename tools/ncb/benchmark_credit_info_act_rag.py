#!/usr/bin/env python3
"""Controlled NCB RAG benchmark based on the iApp OpenThai Legal citation contract."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics
import time
import urllib.request
from pathlib import Path

import psycopg2


LAW = "พระราชบัญญัติการประกอบธุรกิจข้อมูลเครดิต พ.ศ. ๒๕๔๕ (รวมฉบับแก้ไข ๑-๖)"
SYSTEM = ('You are OpenThaiGPT-Legal, an expert assistant on Thai law. You are given a legal '
          'question and the exact statutory sections needed to answer it. Give the final answer in Thai. '
          'Cite ONLY sections present in the provided context, using each section\'s exact law_name and bare '
          'section number (e.g. 132, 77/1). Keep answer under 120 Thai words and cite every applicable provided '
          'section. Output the final answer as JSON: '
          '{"answer": "<Thai answer>", "citations": [{"law": "<law_name>", "section": "<bare id>"}]}.')
SCENARIOS = [
    {"id": "access-log-security", "title": "NCB access log and data-security control", "question": "ในฐานะ IT Internal Audit ของธนาคารสมาชิก NCB จงระบุ control และหลักฐานที่ควรขอจากบริษัทข้อมูลเครดิตเกี่ยวกับความลับ ความมั่นคงปลอดภัย และ audit log ของการเข้าถึงข้อมูลเครดิต", "expected": ["17"], "must": ["ระบบรักษาความลับและความปลอดภัย", "บันทึกและรายงานผลทุกครั้งเมื่อมีผู้เข้าถึง", "ไม่น้อยกว่าสองปี"]},
    {"id": "normal-member-consent", "title": "Member access and consent", "question": "ธนาคารสมาชิกต้องการขอข้อมูลเครดิตลูกค้าเพื่อวิเคราะห์สินเชื่อและออกบัตรเครดิตผ่าน NCB ต้องมีฐานการเปิดเผยใด และกรณีใดที่ข้อยกเว้นไม่ต้องขอความยินยอมเป็นหนังสือ", "expected": ["20"], "must": ["ความยินยอมก่อนทุกครั้ง", "วิเคราะห์สินเชื่อและการออกบัตรเครดิต", "ข้อยกเว้นตามวรรคสอง"]},
    {"id": "loan-broker", "title": "Loan broker forwarding and credit model", "question": "แพลตฟอร์มตัวกลางจัดหาสินเชื่อที่เป็นสมาชิก NCB จะรับข้อมูลเครดิต ส่งต่อให้ผู้ให้สินเชื่อ และใช้ทำ credit model ได้ภายใต้เงื่อนไขใด", "expected": ["24/1", "24/2", "24/3"], "must": ["ความยินยอม", "เปิดเผยเท่าที่จำเป็น", "ข้อมูลที่ระบุตัวบุคคลไม่ได้", "ใช้ model เฉพาะวัตถุประสงค์"]},
    {"id": "correction-dispute", "title": "Customer correction and dispute", "question": "ลูกค้าธนาคารพบข้อมูลเครดิต NCB ผิดและโต้แย้งไม่สำเร็จ ธนาคารสมาชิกและบริษัทข้อมูลเครดิตต้องดำเนินการอย่างไร พร้อม SLA ที่กฎหมายระบุ", "expected": ["25", "26", "27"], "must": ["สิทธิขอแก้ไข/โต้แย้ง", "แจ้งผลพร้อมเหตุผลภายในสามสิบวัน", "บันทึกข้อโต้แย้งในรายงาน", "อุทธรณ์คณะกรรมการ"]},
    {"id": "adverse-decision", "title": "Adverse lending decision", "question": "เมื่อธนาคารปฏิเสธสินเชื่อหรือขึ้นค่าบริการเพราะข้อมูลเครดิต NCB ต้องแจ้งอะไรแก่ลูกค้า และหากข้อมูลผิดลูกค้ามีสิทธิหรือขั้นตอนใด", "expected": ["28", "26", "27"], "must": ["แสดงเหตุผลและแหล่งที่มาของข้อมูลเป็นหนังสือ", "ตรวจสอบโดยไม่เสียค่าธรรมเนียมภายในสามสิบวัน", "ขอให้พิจารณาอีกครั้ง"]},
    {"id": "definitions-scope", "title": "Credit-data definitions and scope", "question": "สำหรับการทำ data inventory ของธนาคารสมาชิก NCB จงแยกความหมายของข้อมูล การประมวลผลข้อมูล ข้อมูลเครดิต คะแนนเครดิต แบบจำลองด้านเครดิต สมาชิก และผู้ใช้บริการ", "expected": ["3"], "must": ["ข้อมูลเครดิต", "คะแนนเครดิต", "แบบจำลองด้านเครดิต", "สมาชิกและผู้ใช้บริการ"]},
    {"id": "license-exclusivity", "title": "License and exclusive operation", "question": "หากกลุ่มธนาคารต้องการตั้งนิติบุคคลเพื่อประกอบธุรกิจข้อมูลเครดิต ต้องผ่านเงื่อนไขการจัดตั้งและใบอนุญาตใด และบุคคลอื่นสามารถประกอบธุรกิจนี้ได้หรือไม่", "expected": ["6", "9"], "must": ["จัดตั้งในรูปบริษัท", "ความเห็นชอบและใบอนุญาตจากรัฐมนตรี", "เฉพาะบริษัทข้อมูลเครดิต"]},
    {"id": "data-lifecycle-location", "title": "Prohibited data, location and retention", "question": "IT Audit พบว่าผู้ประมวลผลข้อมูล NCB เก็บข้อมูลต้องห้าม ประมวลผลนอกประเทศไทย และเก็บข้อมูลเกินอายุ จงระบุข้อห้ามที่ต้องใช้เป็นเกณฑ์ตรวจ", "expected": ["10", "12", "13"], "must": ["ข้อมูลห้ามจัดเก็บ", "ห้ามประมวลผลภายนอกราชอาณาจักร", "อายุข้อมูลตามที่คณะกรรมการกำหนด"]},
    {"id": "member-reporting-quality", "title": "Member reporting, notice and data quality", "question": "ธนาคารสมาชิกส่งข้อมูลลูกค้าเข้า NCB ต้องแจ้งลูกค้าเมื่อใด และต้องควบคุมความถูกต้อง การแก้ไขข้อโต้แย้ง และการรายงานผิดนัดอย่างไร", "expected": ["18", "19"], "must": ["แจ้งภายในสามสิบวัน", "ข้อมูลถูกต้องและทันสมัย", "แก้ไข/ข้อโต้แย้ง", "วันที่เริ่มผิดนัด"]},
    {"id": "purpose-confidentiality", "title": "Purpose limitation and confidentiality", "question": "พนักงานธนาคารและผู้ใช้บริการนำรายงาน NCB ไปใช้หรือเปิดเผยต่อบุคคลอื่นได้เพียงใด และต้องเก็บข้อมูลที่ได้รับตามข้อยกเว้นอย่างไร", "expected": ["22", "23", "24"], "must": ["ใช้ตามวัตถุประสงค์", "ไม่เปิดเผยแก่ผู้ไม่มีสิทธิ", "เก็บเป็นความลับในที่ปลอดภัย", "กลุ่มบุคคลที่ห้ามเปิดเผย"]},
    {"id": "member-credit-model", "title": "Member credit-model governance", "question": "ธนาคารสมาชิกจะใช้ข้อมูล NCB สร้างแบบจำลองด้านเครดิตได้หรือไม่ ต้องลดการระบุตัวบุคคล ขอความยินยอม และจำกัดวัตถุประสงค์อย่างไร", "expected": ["20/1"], "must": ["ไม่มีข้อมูลที่ระบุตัวเจ้าของข้อมูล", "ความยินยอม", "วิเคราะห์สินเชื่อ/บัตรเครดิต/บริหารความเสี่ยง"]},
    {"id": "wrong-data-penalties", "title": "Wrong-data and member-control penalties", "question": "ถ้าธนาคารสมาชิกปกปิดหรือส่งข้อมูลลูกค้าผิด และไม่ปฏิบัติตามหน้าที่แก้ไขข้อมูลหรือ governance ของ credit model มีโทษใดตามเอกสาร", "expected": ["49", "50"], "must": ["ปรับไม่เกินสามแสนบาท", "ปรับรายวันไม่เกินหนึ่งหมื่นบาท", "หน้าที่ตามมาตรา 19/20/1/24/3"]},
    {"id": "unlawful-disclosure-liability", "title": "Unlawful disclosure, civil and criminal consequences", "question": "บริษัทข้อมูลเครดิตเปิดเผยข้อมูลผิดวัตถุประสงค์จนลูกค้าเสียหาย จงแยกความรับผิดทางแพ่ง โทษการเปิดเผยนอกกรอบ และบทบาทของธนาคารแห่งประเทศไทยในคดี", "expected": ["41", "51", "62"], "must": ["ค่าสินไหมทดแทน", "จำคุก/ปรับ", "ธนาคารแห่งประเทศไทยเป็นผู้เสียหาย", "ไม่ตัดสิทธิผู้เสียหายจริง"]},
]


def db():
    return psycopg2.connect(host=os.getenv("OPENGPT_DB_HOST", "127.0.0.1"), port=os.getenv("OPENGPT_DB_PORT", "5432"), dbname=os.getenv("OPENGPT_DB_NAME", "opengpt"), user=os.environ["OPENGPT_DB_USER"], password=os.environ["OPENGPT_DB_PASSWORD"])


def latest_corpus() -> tuple[str, list[dict]]:
    with db() as conn, conn.cursor() as cur:
        cur.execute("select id::text from regulatory_structural_ingest_runs where source_key='credit-info-act-update-1-6' order by created_at desc limit 1")
        run_id = cur.fetchone()[0]
        cur.execute("""select metadata->>'section_id', clause_anchor, page_start, page_end, root_topic,
                       content, embedding from regulatory_structural_chunks where ingest_run_id=%s
                       order by page_start, clause_anchor, (metadata->>'part')::int""", (run_id,))
        raw = cur.fetchall()
    grouped: dict[str, dict] = {}
    for section, anchor, p1, p2, topic, content, vector in raw:
        row = grouped.setdefault(section, {"section": section, "anchor": anchor, "page_start": p1, "page_end": p2, "topic": topic, "content": [], "vectors": []})
        row["content"].append(content)
        row["vectors"].append(vector)
    rows = []
    for row in grouped.values():
        # Whole-section files are what Open WebUI receives.  Vector is a mean only
        # for retrieval scoring when an exceptional long section has multiple parts.
        row["content"] = " ".join(row["content"])
        row["vector"] = [sum(values) / len(values) for values in zip(*row.pop("vectors"))]
        rows.append(row)
    return run_id, rows


def embed(question: str, endpoint: str, model: str) -> list[float]:
    request = urllib.request.Request(endpoint, data=json.dumps({"model": model, "input": [question]}, ensure_ascii=False).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode())["data"][0]["embedding"]


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right)) / (math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right)))


def retrieve(question: str, corpus: list[dict], endpoint: str, model: str, top_k: int = 4) -> list[dict]:
    vector = embed(question, endpoint, model)
    return sorted(corpus, key=lambda row: cosine(vector, row["vector"]), reverse=True)[:top_k]


def packet(evidence: list[dict]) -> str:
    # The self-hosted OpenThai server deliberately has a 4,096-token context.
    # Keep every selected section identifiable, but cap its quoted body so a
    # top-4 retrieval packet cannot crowd out the answer or fail the request.
    return "\n\n".join(f"[law_name: {LAW}; section: {row['section']}; PDF pp. {row['page_start']}-{row['page_end']}]\n{row['content'][:1600]}" for row in evidence)


def call(endpoint: str, model: str, question: str, evidence: list[dict], closed_book: bool, max_tokens: int) -> tuple[str, dict, float]:
    user = question if closed_book else f"Provided context:\n{packet(evidence)}\n\nQuestion: {question}"
    payload = {"model": model, "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}], "temperature": 0.0, "max_tokens": max_tokens, "stream": False, "chat_template_kwargs": {"enable_thinking": False}}
    started = time.perf_counter()
    req = urllib.request.Request(endpoint, data=json.dumps(payload, ensure_ascii=False).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as response:
        body = json.loads(response.read().decode())
    return (body["choices"][0]["message"].get("content") or "").strip(), body.get("usage", {}), round((time.perf_counter() - started) * 1000, 1)


def cited_sections(answer: str) -> list[str]:
    # Handles strict JSON as well as a model that wraps its JSON in Markdown.
    match = re.search(r"\{[\s\S]*\}", answer)
    if match:
        try:
            payload = json.loads(match.group(0))
            return [str(item.get("section")) for item in payload.get("citations", []) if item.get("section") is not None]
        except json.JSONDecodeError:
            pass
    return re.findall(r'"section"\s*:\s*"?([0-9/]+)', answer)


def score(answer: str, expected: list[str], available: list[dict], closed_book: bool) -> dict:
    cited = set(cited_sections(answer)); expected_set = set(expected); allowed = {item["section"] for item in available}
    return {"cited": sorted(cited), "json_valid": bool(re.search(r"\{[\s\S]*\}", answer) and cited_sections(answer) is not None),
            "grounded_citation_precision": round(len(cited & allowed) / len(cited), 3) if cited and not closed_book else None,
            "expected_citation_precision": round(len(cited & expected_set) / len(cited), 3) if cited else 0.0,
            "citation_recall": round(len(cited & expected_set) / len(expected_set), 3),
            "unsupported": sorted(cited - allowed) if not closed_book else sorted(cited - expected_set)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True); parser.add_argument("--model", required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--embedding-endpoint", default="http://127.0.0.1:8082/v1/embeddings")
    parser.add_argument("--embedding-model", default="Qwen3-Embedding-4B")
    parser.add_argument("--max-tokens", type=int, default=700)
    parser.add_argument("--modes", default="open_book_echo,open_book_selection,vector_retrieval_top4,closed_book_control")
    parser.add_argument("--scenario-ids", default="", help="Comma-separated scenario ids; empty runs all")
    args = parser.parse_args(); args.outdir.mkdir(parents=True, exist_ok=True)
    run_id, corpus = latest_corpus(); by_section = {row["section"]: row for row in corpus}
    distractors = [by_section[key] for key in ("39", "41", "62")]
    results = []
    requested_scenarios = {value for value in args.scenario_ids.split(",") if value}
    scenarios = [item for item in SCENARIOS if not requested_scenarios or item["id"] in requested_scenarios]
    if requested_scenarios - {item["id"] for item in scenarios}:
        raise ValueError(f"unknown scenario ids: {sorted(requested_scenarios - {item['id'] for item in scenarios})}")
    for scenario in scenarios:
        exact = [by_section[key] for key in scenario["expected"]]
        modes = [("open_book_echo", exact, False), ("open_book_selection", exact + distractors, False), ("vector_retrieval_top4", retrieve(scenario["question"], corpus, args.embedding_endpoint, args.embedding_model), False), ("closed_book_control", [], True)]
        requested_modes = set(args.modes.split(","))
        modes = [item for item in modes if item[0] in requested_modes]
        for mode, evidence, closed in modes:
            try:
                answer, usage, elapsed = call(args.endpoint, args.model, scenario["question"], evidence, closed, args.max_tokens)
                result = {"scenario": scenario, "mode": mode, "evidence_sections": [item["section"] for item in evidence], "answer": answer, "usage": usage, "generation_ms": elapsed, **score(answer, scenario["expected"], evidence, closed)}
            except Exception as exc:  # retain the remaining scenarios for diagnosis
                result = {"scenario": scenario, "mode": mode, "evidence_sections": [item["section"] for item in evidence], "answer": "", "usage": {}, "generation_ms": 0.0, "cited": [], "json_valid": False, "grounded_citation_precision": None, "expected_citation_precision": 0.0, "citation_recall": 0.0, "unsupported": [], "error": f"{type(exc).__name__}: {exc}"}
            results.append(result)
            (args.outdir / "results.partial.json").write_text(json.dumps({"structural_ingest_run": run_id, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"{scenario['id']} {mode}: {elapsed / 1000:.2f}s", flush=True)
    times = [row["generation_ms"] for row in results]
    output = {"structural_ingest_run": run_id, "model": args.model, "endpoint": args.endpoint, "test_basis": "Open WebUI-style retrieved context + iApp JSON citation contract", "results": results, "mean_generation_ms": round(statistics.mean(times), 1), "median_generation_ms": round(statistics.median(times), 1)}
    (args.outdir / "results.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# Credit-information Act NCB RAG benchmark — {args.model}", "", f"- Structural ingest run: `{run_id}`", f"- Scenarios: {len(scenarios)}; modes: {', '.join(sorted(set(args.modes.split(','))))}.", "- Citation contract and generation settings follow the iApp OpenThai 2.0 Legal API guide: JSON citations, temperature 0, thinking off.", "- This controlled retrieval is Qwen3-Embedding-4B dense-vector top-4; it is not a substitute for the hosted API's BM25 + vector + reranker pipeline.", "- Grounded precision = citations among supplied sections. Relevant precision/recall = citations against the expected section set; this exposes distractor selection errors.", "", "| Scenario | Mode | Retrieved / supplied sections | Time | Grounded P | Relevant P | Recall | Unsupported |", "|---|---|---|---:|---:|---:|---:|---|"]
    for row in results:
        precision = "—" if row["grounded_citation_precision"] is None else f"{row['grounded_citation_precision']:.0%}"
        lines.append(f"| {row['scenario']['title']} | {row['mode']} | {', '.join(row['evidence_sections']) or 'none'} | {row['generation_ms']/1000:.2f}s | {precision} | {row['expected_citation_precision']:.0%} | {row['citation_recall']:.0%} | {', '.join(row['unsupported']) or '—'} |")
    lines.extend(["", "## Full outputs", ""])
    for row in results:
        lines.extend([f"## {row['scenario']['title']} — {row['mode']}", "", f"- Expected legal sections: {', '.join(row['scenario']['expected'])}", f"- Evidence supplied: {', '.join(row['evidence_sections']) or 'none'}", f"- Cited sections parsed: {', '.join(row['cited']) or 'none'}", f"- Request time: {row['generation_ms']/1000:.2f}s", "", row["answer"], ""])
    (args.outdir / "report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
