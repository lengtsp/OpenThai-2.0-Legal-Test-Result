---
name: extract-structural-legal-chunks
description: Extract high-quality, page-anchored structural chunks from legal, regulatory, policy, audit, and banking PDFs. Use when Codex must prepare PDFs for RAG/Open WebUI, split Thai statutes by หมวด/มาตรา instead of arbitrary windows, remove headers/footnotes/OCR noise, preserve section and page provenance, export section-level Markdown/JSONL, or diagnose poor retrieval caused by bad chunk boundaries.
---

# Extract Structural Legal Chunks

Build an auditable corpus whose retrieval unit matches the document's legal unit. Prefer one complete clause or section over fixed-size chunks.

## Workflow

1. Create a source manifest.
   - Record filename, title, issuer, source URL/path, SHA-256, page count, extraction method, and timestamp.
   - Decide whether amendment appendices belong in the active-law corpus or a separate historical corpus.

2. Inspect the PDF before parsing.
   - Check bookmarks, text-layer quality, page layout, font sizes, repeated headers/footers, footnote location, Thai numeral handling, and whether headings span separate lines.
   - Render or inspect suspicious pages; do not trust plain-text order blindly.

3. Choose the structural unit.
   - Statutes: `law → chapter → section → paragraph/subparagraph`.
   - Regulations/policies: `document → part → heading → numbered requirement`.
   - Keep one `มาตรา` or requirement per chunk when it fits the model context.
   - Split only oversized units with recursive legal-boundary/whitespace
     splitting, retaining the same clause id and adding `part/parts`.

4. Run deterministic extraction.
   - Use `scripts/extract_structural_pdf.py` for Thai section-based PDFs.
   - Tune `--page-end` to exclude historical amendment appendices from the current-law corpus.
   - Tune `--bottom-note-ratio` only after visually checking footnote placement.

5. Normalize without destroying legal meaning.
   - Collapse layout whitespace.
   - Canonicalize heading ids and Thai/Arabic numerals in metadata.
   - Remove repeated page headers/footers and amendment-history footnotes from the body.
   - Never remove paragraph numbers, exceptions, deadlines, negation, or cross-references.

6. Attach provenance to every chunk.
   - Require `law_name`, `section_id`, `section_heading`, `topic`, `page_start`, `page_end`, `source_url`, content hash, structural path, and part metadata.
   - Keep page numbers even when exporting one-section Markdown files.

7. Run quality gates before embedding.
   - Read `references/quality-gates.md`.
   - Reject duplicate active section ids, missing pages, empty chunks,
     footnote-only chunks, headings fused with footnote markers, chapter
     titles with fused note numbers, and references misclassified as new headings.
   - Manually inspect at least: first section, longest section, page-spanning section, slash section (`24/1`), footnote-heavy section, and final active section.

8. Embed and retrieve only after the structural corpus passes.
   - Keep the embedding model identical for indexing and queries.
   - For Thai law, combine lexical/BM25 and embeddings, then rerank.
   - Deduplicate candidates by `(law_name, section_id)` before generation.
   - Inject the smallest complete evidence set and validate citations after generation.

9. Evaluate each question separately.
   - Test exact-context echo, relevant-plus-distractor selection, real retrieval, and closed-book control.
   - Log selected pages/sections, answer, citations, latency, and failure layer.
   - Diagnose retrieval separately from answer generation.

## NCB Pattern

For the consolidated Credit Information Act:

```bash
python scripts/extract_structural_pdf.py \
  --pdf "Credit Info Act update 1-6.pdf" \
  --out-dir out/credit-info-act \
  --law-name "พระราชบัญญัติการประกอบธุรกิจข้อมูลเครดิต พ.ศ. ๒๕๔๕ (รวมฉบับแก้ไข ๑-๖)" \
  --source-url "https://www.creditinfocommittee.or.th/api/file/pdf/law_act/Credit%20Info%20Act%20update%201-6.pdf" \
  --page-end 21 \
  --max-chars 4000
```

The `--page-end 21` boundary keeps amendment-history appendices separate from the current consolidated sections. Read `references/ncb-example.md` for the concrete failure modes and retrieval examples.

## Output Contract

Expect:

- `manifest.json`: source and build provenance plus quality summary;
- `chunks.jsonl`: complete machine-readable structural chunks;
- `openwebui/*.md`: one section-oriented file per active legal section;
- `quality.json`: deterministic checks requiring review.

Do not claim the corpus is production-ready merely because the script exits successfully. Review the quality report and sampled source pages first.
