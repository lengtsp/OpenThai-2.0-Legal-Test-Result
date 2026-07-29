# BOT RAG evaluation — OpenThai2.0 Legal

Test date: 29 July 2026.  Service under test: `http://127.0.0.1:8083/api/chat`; model: `openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b` on vLLM `127.0.0.1:3033`.

## Grounded corpus

The production test corpus contains five short, source-preserved chunks from official Bank of Thailand pages. Each chunk keeps its source URL in `source_url`, document title, and a logical section label.

| Source | Chunks used | Purpose |
|---|---:|---|
| [MPC result 1/2569 — 25 Feb 2026](https://www.bot.or.th/th/news-and-media/news/mpc/news-20260225-5aG7DDZ1.html) | 2 | Decision/vote plus rationale |
| [Foreign-exchange control rules](https://www.bot.or.th/th/our-roles/financial-markets/foreign-exchange-regulations/foreign-exchange-laws.html) | 3 | authorised-dealer rule, inbound FX, outbound payments/gift limit |

The earlier three legal demo chunks were removed after the experiment; the active corpus is BOT-only (5 chunks). Each chunk is deliberately small enough to support section-level selection and inspectable citations.

## Test design and results

| ID | Mode / question | Expected evidence and acceptance criterion | Result | Timing |
|---|---|---|---|---:|
| U1 | Open-book factual: MPC decision and vote on 25 Feb 2569 | MPC decision chunk; `1.25 → 1.00`, cut `0.25`, vote `4:2` | Pass. Answer cited `[1]` and all four facts were correct. | 5.59 s |
| U2 | Open-book synthesis: rationale and dissent | MPC rationale + decision | Content pass: accurately stated support for recovery/SMEs/households/inflation expectation and dissent. Citation-in-text failed in the first run. | 13.04 s |
| U3 | Numeric legal-like retrieval: USD 12m export receipt | FX §2.1; threshold `>= USD 10m`, return and sell/deposit within `360` days | Pass. Correct threshold, deadline, and bank action; cited `[1]`. | 7.26 s |
| U4 | Rule selection: where to execute FX transactions | FX general rule; authorised persons/dealers | Pass. Correctly named authorised FX-business operators and cited `[1]`. | 6.57 s |
| U5 | Numeric limit: gratuitous transfer abroad | FX §2.2; `USD 200,000` equivalent/person/year | Pass. Correct value and scope; cited `[1]`. | 3.42 s |
| U6 | Grounded abstention: licensing of digital-asset trading providers | No direct corpus evidence | First run failed: model fabricated a digital-asset licensing rule. After adding strict evidence rules, rerun passed substantively: it said the corpus does not cover the question and requested an official digital-asset source. | 10.24 s → 9.09 s |
| U7 | Closed-book baseline: same MPC decision, RAG off | Should not be trusted without source | Fail, as intended baseline: model said `1.875%`, vote `4:1`, and emitted an unsupported `[1]`. This demonstrates why retrieval is required for current regulatory facts. | 4.03 s |
| U8 | Multi-turn session: follow-up asks prior rate/effective date | PostgreSQL history plus MPC chunk | Pass. Correctly returned `1.25%` before reduction and “effective immediately”; cited `[1]`. | 2.36 s |

Retrieval in the five-chunk local corpus was 0.8–3.6 ms. End-to-end model generation was 2.36–13.04 s, driven mainly by output length. These figures are local single-user measurements, not a throughput benchmark.

## Evidence and citation assessment

- Factual/numeric retrieval: 4/4 direct scenarios passed (U1, U3–U5). The correct chunk was ranked first and the answer used that citation.
- Synthesis: content was grounded, but U2 showed that prompting alone does not guarantee inline citations. The UI still exposes all source chunks below each response, but this is weaker than a per-claim citation contract.
- Abstention: a naïve RAG prompt was unsafe when distractors were present. The strict evidence gate now explicitly prohibits cross-topic inference and fabricated section numbers. On rerun with the BOT-only corpus, the model abstained correctly.
- Closed-book: current, date-sensitive BOT facts must not be trusted without retrieval. U7 was materially wrong on both the rate and vote.

## Changes made from the evaluation

1. Added `source_url` to a corpus row and returns it with every retrieval hit, preventing source URLs from being truncated in the short `section` label.
2. Added a strict RAG contract to the system prompt: direct evidence only, intentional-distractor awareness, no cross-topic inference, no invented section numbers, and a prescribed abstention path.
3. Retained full retrieved chunks, source labels, per-message timing, token usage, and citations in the PostgreSQL chat-session record.

## Recommended next tests

1. Ingest official source pages as one logical section per chunk and retain publication/effective date metadata.
2. Add a deterministic citation validator: flag an answer with material claims but no `[n]`, then retry once with a compact citation-only repair prompt.
3. Use a held-out set of BOT facts plus known near-miss chunks to measure retrieval Recall@k, citation precision/recall/F1, abstention accuracy, and latency separately.
4. Add a semantic Thai embedding/reranker only after this BM25 baseline is recorded; compare it against the same held-out cases rather than replacing the baseline blindly.
