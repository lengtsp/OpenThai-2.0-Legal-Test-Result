# NCSA RAG benchmark — OpenThai2.0 vs Qwen3.6-27B

## Result

Qwen3.6-27B was preferred for this page-grounded NCSA RAG replay: it supplied strict page/chunk citations in all ten answers and had lower mean model-request latency. OpenThai2.0 remained substantively useful, especially for incident response, third-party risk, and configuration, but supplied the required strict citation syntax in only five answers.

| Metric | OpenThai2.0 Legal | Qwen3.6-27B |
|---|---:|---:|
| Questions | 10 | 10 |
| Recursive chunks | 1,497 | 1,497 |
| Mean request latency | 23.96 s | **21.77 s** |
| Median request latency | 23.96 s | **20.29 s** |
| Total request time | 239.61 s | **217.72 s** |
| Strict `[p.x c.y]` citations | 5/10 | **10/10** |
| Codex judge score | 7.85/10 | **9.20/10** |

Qwen's end-to-end runner wall time was 222.00 seconds, including local retrieval and report generation. The latency table measures the HTTP model request only and excludes model loading.

## Reproducible test contract

- Source: NCSA cyber-security compendium document `16122`, 629 pages.
- Extraction: PyMuPDF recursive chunks, 1,200-character chunk size, 250-character overlap.
- Retrieval: same in-memory BM25, top 3 chunks for every question.
- Workload: 10 Thai IT-internal-audit scenarios: CII scope, governance, risk assessment, monitoring, incident response/reporting, third party, configuration, awareness, and risk-proportional conclusion.
- Prompt: separates documentary facts from audit recommendations, requires `[p.x c.y]` citations, and requires an explicit evidence gap when the supplied chunks are insufficient.
- Generation: sequential requests, temperature 0.1, maximum 650 tokens.
- OpenThai baseline: vLLM on `127.0.0.1:3033`.
- Qwen candidate: Qwen3.6-27B GGUF Q8_K_XL via llama.cpp on `127.0.0.1:8081`, text-only, reasoning off, 12k context.

This is an operational RAG comparison. The two runtimes and model representations differ, so the result should not be treated as an architecture-only quality claim. The evidence packet, question set, prompt intent, temperature, and completion cap were fixed.

## Codex judge rubric

Each answer was reviewed against the selected page/chunk evidence.

- Evidence grounding and relevance: 0–4
- Citation coverage and traceability: 0–3
- Requirement/audit-recommendation separation and usefulness: 0–2
- No material unsupported assertion or appropriate evidence-gap handling: 0–1

| Scenario | OpenThai | Qwen | Judge conclusion |
|---|---:|---:|---|
| CII scope | 5.5 | **8.0** | Qwen cites the banking CII sector; both partly conflate CII scope with threat-severity criteria. |
| Governance | 6.5 | **9.5** | Qwen traces Three Lines, independence, Head of Information Security, and CIRT roles. |
| Risk assessment | 6.5 | **9.0** | Qwen anchors risk framework, appetite, register, monitoring, and minimum controls. |
| Monitoring | 8.5 | **9.0** | Both useful; distinguish coordination-centre responsibilities from bank implementation. |
| Incident response | **10.0** | **10.0** | Strong evidence use, cadence, and audit artefacts. |
| Incident reporting | 8.0 | **9.5** | Qwen anchors reporting and evidence preservation without inventing a deadline. |
| Cloud and third party | **10.0** | **10.0** | Strong SLA, supplier-risk, access-control, and audit-right coverage. |
| Configuration | **10.0** | **10.0** | Audit-ready configuration controls and sampling guidance. |
| Awareness | 7.0 | **9.5** | Qwen consistently cites awareness, annual review, and information sharing. |
| Risk-proportional conclusion | 6.5 | **7.5** | The top-3 evidence packet is too narrow for enterprise-wide priority ranking. |

## Per-question latency

| Q | Scenario | OpenThai | Qwen |
|---|---|---:|---:|
| 1 | CII scope | 24.54 s | **23.75 s** |
| 2 | Governance | **25.20 s** | 30.86 s |
| 3 | Risk assessment | 26.17 s | **25.06 s** |
| 4 | Monitoring | 25.54 s | **21.56 s** |
| 5 | Incident response | 25.18 s | **19.70 s** |
| 6 | Incident reporting | 23.12 s | **20.81 s** |
| 7 | Cloud and third party | 23.38 s | **19.33 s** |
| 8 | Configuration | 22.32 s | **19.77 s** |
| 9 | Awareness | 22.67 s | **18.14 s** |
| 10 | Risk-proportional conclusion | 21.49 s | **18.74 s** |

## Audit recommendation

Use Qwen3.6-27B for this NCSA page-grounded RAG lane when strict citation compliance is a hard requirement. Retain the citation contract and add a retrieval-quality gate for CII scoping and enterprise-wide risk-priority conclusions; a small, unbalanced evidence packet must not be represented as conclusive.
