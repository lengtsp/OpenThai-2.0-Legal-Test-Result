#!/usr/bin/env python3
"""Export the persisted statute as one Open WebUI-ready Markdown file per section."""

from __future__ import annotations

import os
import re
from pathlib import Path

import psycopg2


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data/credit_info_act/openwebui_knowledge"
SOURCE = "https://www.creditinfocommittee.or.th/api/file/pdf/law_act/Credit%20Info%20Act%20update%201-6.pdf"
LAW = "พระราชบัญญัติการประกอบธุรกิจข้อมูลเครดิต พ.ศ. ๒๕๔๕ (รวมฉบับแก้ไข ๑-๖)"


def connection():
    return psycopg2.connect(host=os.getenv("OPENGPT_DB_HOST", "127.0.0.1"), port=os.getenv("OPENGPT_DB_PORT", "5432"), dbname=os.getenv("OPENGPT_DB_NAME", "opengpt"), user=os.environ["OPENGPT_DB_USER"], password=os.environ["OPENGPT_DB_PASSWORD"])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with connection() as db, db.cursor() as cur:
        cur.execute("""SELECT id::text FROM regulatory_structural_ingest_runs
            WHERE source_key='credit-info-act-update-1-6' ORDER BY created_at DESC LIMIT 1""")
        run_id = cur.fetchone()[0]
        cur.execute("""SELECT metadata->>'section_id', clause_anchor, root_topic, page_start, page_end,
                       string_agg(content, ' ' ORDER BY (metadata->>'part')::int)
            FROM regulatory_structural_chunks WHERE ingest_run_id=%s
              AND root_topic NOT LIKE 'ภาคผนวก%%'
            GROUP BY metadata->>'section_id', clause_anchor, root_topic, page_start, page_end
            ORDER BY page_start, clause_anchor""", (run_id,))
        rows = cur.fetchall()
    index = ["# Open WebUI Knowledge upload manifest", "", f"- Ingest run: `{run_id}`", f"- Law: {LAW}", f"- Files: {len(rows)} (one legal section per file)", "", "| File | Section | Pages | Topic |", "|---|---|---:|---|"]
    for section, anchor, topic, first_page, last_page, content in rows:
        safe = re.sub(r"[^0-9A-Za-z/_-]+", "_", section).replace("/", "-")
        filename = f"credit-info-act-section-{safe}.md"
        markdown = f"""---
law_name: \"{LAW}\"
section: \"{section}\"
source_url: \"{SOURCE}\"
page_start: {first_page}
page_end: {last_page}
structural_topic: \"{topic}\"
---

# {anchor}

{content.strip()}

Source: {SOURCE} (PDF pp. {first_page}-{last_page})
"""
        (OUT / filename).write_text(markdown, encoding="utf-8")
        index.append(f"| `{filename}` | {anchor} | {first_page}-{last_page} | {topic} |")
    (OUT / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    print(f"{len(rows)} files exported to {OUT}")


if __name__ == "__main__":
    main()
