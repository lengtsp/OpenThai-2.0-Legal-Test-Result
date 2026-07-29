# Controlled NCSA RAG benchmark — fixed evidence

## Purpose

This rerun separates retrieval from answer generation. Seven audit scenarios each receive a fixed, page-anchored NCSA evidence packet and an explicit checklist of required concepts. Both models use the same Thai prompt, evidence, temperature 0.0, 600-token cap, and sequential execution.

The first OpenThai attempt was discarded because reasoning text was returned. The valid run used vLLM `enable_thinking=false` and a probe confirmed that only the final answer was returned.

## Result

| Metric | OpenThai2.0 Legal | Qwen3.6-27B |
|---|---:|---:|
| Scenarios | 7 | 7 |
| Mean model-request latency | 21.60 s | **19.33 s** |
| Strict `[p.x c.y]` citation syntax | 4/7 | **7/7** |
| Mean strict fixed-chunk citation recall | 47.6% | **90.5%** |
| Strict out-of-packet citation | 0 | 0 |
| Codex content coverage | 25/26 | **26/26** |

Qwen is 10.5% faster and consistently meets the machine-verifiable page/chunk citation contract. OpenThai is substantively strong: its weaker strict score is mostly a citation-format issue, including `(p.278 c.1)` and abbreviated `(ค.1)` forms rather than the required `[p.278 c.1]` form.

## Scenario detail

| Scenario | OpenThai | Qwen | Codex finding |
|---|---:|---:|---|
| Governance and independence | 22.35 s · 100% recall | **18.07 s · 100%** | Both cover Three Lines, roles and independence. |
| Risk and minimum controls | 21.35 s · 0% strict | **18.02 s · 67%** | Both cover framework, appetite/register and controls; OpenThai delimiter is nonconforming. |
| Incident readiness | 21.36 s · 100% | **18.00 s · 100%** | Both correctly cover annual review, communication, significant-change review and crisis plan. |
| Incident reporting/evidence | 22.70 s · 33% | **21.34 s · 67%** | Qwen has fuller traceability; both avoid inventing a deadline. |
| Cloud / third party | 20.82 s · 0% strict | **20.08 s · 100%** | Both cover SLA, supplier risk, audit rights and access logs. |
| Configuration | 21.10 s · 100% | **19.91 s · 100%** | Both audit-ready and grounded. |
| Awareness / sharing | 21.53 s · 0% strict | **19.86 s · 100%** | OpenThai covers content but abbreviates citations; Qwen retains all anchors. |

## Recommendation

Use Qwen3.6-27B for a page-grounded NCSA audit RAG lane when strict citations are mandatory. Retain OpenThai for legal/audit synthesis only behind a citation validator or normalizer that rejects nonconforming formats before an answer enters an audit workpaper.
