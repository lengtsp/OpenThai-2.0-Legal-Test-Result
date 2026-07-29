# Methodology and format comparison

## Corpus audit

| Item | Original Open WebUI v2 | NitiBench-compatible projection |
|---|---|---|
| Legal unit | one active section per `.md` file | one record per active section |
| Primary fields | `<law law_name="..." section="...">` plus external manifest | `law_name`, `section_num`, `section_content` |
| Traceability | page/topic in manifest | retained as per-record metadata: page range, topic, source URL, SHA-256 and structural path |
| Records | 73 | 73 |
| Answer/ground-truth leakage | none | none |
| Cleanup | final file included non-operative promulgation note | note removed from section 66; its page range ends at 21 |

This is compatible with the core NitiBench law-chunk pattern: law name, bare section number, and the statutory text beginning with the law/section. The projection intentionally retains extra metadata because Open WebUI/RAG auditing needs page provenance even though the minimal NitiBench fields do not require it.

Quality gates passed: required fields present, canonical heading at the start of each record, no duplicate section, valid page range, 64-character content hash, and no remaining promulgation note.

## Test design

Six NCB scenarios were fixed before execution. Expected routes were derived from the supplied statutory records: 20; 20+22; 28; 19+26; 24+54; and 20/1. The scenario set checks consent scope, marketing use, adverse action notice, correction, employee confidentiality and credit modelling.

Each model receives the same Thai question and the same citation instruction. The modes differ only in evidence:

| Mode | Evidence |
|---|---|
| Echo | exact expected section(s) only |
| Selection | expected section(s) plus sections 39, 41 and 62 as near-miss distractors |
| RAG top-5 | five sections retrieved by cosine similarity from the 73-record corpus using Qwen3-Embedding-4B |

The answer must be JSON and may cite only supplied sections. Citation precision/recal are deterministic exact-match measures over section numbers; JSON validity is checked after each call. All 36 responses, supplied section IDs and latency are retained in the raw packet.

## Before/after retrieval check

This auxiliary comparison uses the same six queries, Qwen3-Embedding-4B and cosine top-5. It isolates chunk representation/cleanup, not generation quality.

| Scenario | Expected | Open WebUI v2 top-5 recall | Projection top-5 recall | Interpretation |
|---|---:|---:|---:|---|
| Consent annual review | 20 | 0.00 | 1.00 | projection moves 20 into top-5 |
| Cross-selling | 20, 22 | 1.00 | 0.50 | projection loses 22 from top-5 |
| Adverse notice | 28 | 1.00 | 1.00 | unchanged |
| Wrong data correction | 19, 26 | 1.00 | 1.00 | unchanged |
| Employee leak | 24, 54 | 0.00 | 0.00 | both fail |
| Credit model | 20/1 | 1.00 | 1.00 | unchanged |
| **Macro mean** | — | **0.667** | **0.750** | too small/mixed to claim a general improvement |

The right conclusion is therefore: **the projection is a safer data contract and produces a small positive result in this sample, but field normalization alone does not solve the hard retrieval cases.**

## Failure analysis and next changes

1. **Employee leak:** neither format retrieves the operative confidentiality section 24 nor its sanction 54. Add a hybrid BM25/keyword route for `เปิดเผย`, `ความลับ`, `พนักงาน`, `แชต`, and a legal relation expansion from a prohibition section to its penalty section.
2. **Cross-selling:** dense search finds consent/model sections but can miss section 22's use-purpose/non-disclosure duty. Add synonym-rich retrieval text and rerank on actor + action + purpose; require both disclosure and use-purpose checks for marketing queries.
3. **Citation discipline:** both models sometimes cite a supplied but non-applicable section. Validate citations against an allowed reranked set and display the source excerpt with every citation.
4. **Production safety:** perform law/version routing first, preserve `law_name`, page and section provenance, and have legal/compliance review citations. These scores are not a substitute for legal advice or an official model benchmark.

## Codex reviewer rubric

Codex manually reviewed the preserved outputs after deterministic metrics were calculated. Each answer received 0–3:

- **3** — correct operational conclusion, material statutory condition/actor/deadline covered, and no material misleading claim.
- **2** — materially useful and directionally correct, but a required condition or citation is incomplete/extra.
- **1** — partly useful but legal route, citation or effect is materially unreliable.
- **0** — wrong core conclusion or materially unsupported legal outcome.

The reviewer is not a lawyer. This assessment is traceable to the raw answers and is intentionally reported separately from exact citation metrics.
