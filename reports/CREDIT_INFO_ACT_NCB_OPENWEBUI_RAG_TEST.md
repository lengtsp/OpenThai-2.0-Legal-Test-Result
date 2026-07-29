# NCB Credit Information Act — Structural RAG and Open WebUI readiness test

## Scope and provenance

- Official source: [Credit Info Act update 1-6.pdf](https://www.creditinfocommittee.or.th/api/file/pdf/law_act/Credit%20Info%20Act%20update%201-6.pdf)
- SHA-256: `324e4087ea90bcb1467ebc379bd665e902ecc142737c60e102ea5425df0f732a`
- Extraction: PyMuPDF text layer, with Thai `หมวด` / `มาตรา` hierarchy and PDF page anchors.
- PostgreSQL database: `opengpt`, tables `regulatory_structural_ingest_runs` and `regulatory_structural_chunks`.
- Final ingest run: `d0ee0542-5464-4d66-83b3-89d8847059e8`.
- 24 PDF pages, 79 legal sections, 80 structural chunks, and 2,560-dimensional `Qwen3-Embedding-4B` vectors.

The one extra chunk is a section whose source text is longer than the configured 4,000-character limit. Its parts retain the same section id and are reassembled before Open WebUI upload.

## Open WebUI Knowledge-base package

The ready-to-upload package is [`data/credit_info_act/openwebui_knowledge`](../data/credit_info_act/openwebui_knowledge/README.md): 73 Markdown files, one current consolidated legal section per file. Historical amendment appendices are retained in PostgreSQL but excluded from the Knowledge upload so an amendment's transitional section cannot overwrite a current section with the same number. Each upload file has `law_name`, bare `section`, original PDF pages, source URL, and structural topic as front matter.

Use this sequence in an Open WebUI instance:

1. Add the OpenAI-compatible connection for the local OpenThai service. For an Open WebUI container use `http://host.docker.internal:3033/v1`; for a host-native installation use `http://127.0.0.1:3033/v1`. Select model `openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b`.
2. Go to **Workspace → Knowledge → + Create a Knowledge base** and name it `NCB — Credit Information Act (update 1-6)`.
3. Upload the 73 section files. Do not upload the package `README.md`, as it is only an audit manifest.
4. Start a chat, type `#`, select that Knowledge base, and send one of the scenario prompts below. Alternatively attach the Knowledge base permanently to a custom model in **Workspace → Models**.
5. Display retrieved sections with their file name and page metadata next to every answer; retain the returned JSON citations for a post-answer validator.

The Open WebUI live-service verification and Knowledge import result are recorded in the “Live Open WebUI test” section below.

## Prompt contract used

The test follows the iApp guide: temperature `0`, thinking disabled, and its JSON citation contract. It tells the model to cite only the supplied context by exact law name and bare section number.

The original live Open WebUI run used an 8,192-token context window and a
2,048-token answer cap. The service was subsequently expanded to 12,288 tokens
for a long-context benchmark with a 4,096-token answer cap. Both pass
`enable_thinking=false`; output budget remains intentionally separate from
context size.
Increasing context allows a larger retrieved evidence packet plus chat history,
whereas increasing `max_tokens` allows a longer answer. The sum of prompt and
generated tokens must remain within the configured context limit. FlashAttention 2
remains enabled for attention; only the FlashInfer top-k/top-p sampler is
disabled because its JIT cache path in the original virtual environment
contained spaces. vLLM falls back to its native sampler for that operation.

For production, also enforce these checks after generation:

- response is valid JSON;
- every citation exists in the retrieved section set;
- section ids are de-duplicated;
- a low retrieval score, an empty citation list, or an incomplete JSON response is shown as an evidence gap, not a legal conclusion.

## NCB scenarios tested

| Scenario | Expected sections | What it tests |
|---|---|---|
| Access logs and data security | 17 | Security controls, access logging, and two-year log retention |
| Member consent | 20 | Credit-data disclosure for lending/card analysis and statutory exceptions |
| Loan-broker flow | 24/1, 24/2, 24/3 | Consent, necessary onward disclosure, de-identified credit models |
| Correction and dispute | 25, 26, 27 | Data-subject rights, 30-day outcome notice, dispute annotation and appeal |
| Adverse decision | 28, 26, 27 | Written reason/source, fee-free verification window, reconsideration |

## Measured OpenThai results

All timings are request-to-response only; model loading and embedding time are excluded. “Grounded precision” checks whether a citation was in the provided packet. “Relevant precision/recall” checks it against the expected legal sections.

| RAG mode | Mean time | Grounded precision | Relevant precision | Relevant recall | Interpretation |
|---|---:|---:|---:|---:|---|
| Open-book echo: exact sections supplied | 11.15s | 100% | 100% | 100% | Best-case grounding works across all five scenarios. |
| Open-book selection: exact sections plus 39/41/62 distractors | 13.01s | 100% | 70.0% | 86.7% | The model sometimes cites supplied but irrelevant distractors; selection must be improved before generation. |
| Dense retrieval: Qwen embedding top-4 | 14.88s | 100% | 40.0% | 66.7% | Retrieval included relevant sections often, but also close legal neighbours and missed sections in multi-section scenarios. |

Full request/response evidence is in the
[baseline benchmark report](NCB_OPENTHAI_BASELINE_RAG_BENCHMARK.md) and
machine-readable data in `../results/ncb/openthai_baseline/results.json`.

## Extended eight-scenario result

Eight additional scenarios cover definitions, licensing, prohibited data/location/retention, member reporting and data quality, purpose limitation, credit-model governance, member penalties, and unlawful disclosure:

| Mode | Mean time | Grounded precision | Relevant precision | Relevant recall | Exact citation sets |
|---|---:|---:|---:|---:|---:|
| Exact structural sections | 11.71s | 100% | 100% | 100% | 8/8 |
| Dense Qwen embedding top-4 | 12.90s | 100% | 51.0% | 81.2% | 1/8 |

The extended result reinforces the same conclusion: structural preparation
solves generation when the correct evidence is selected, while dense retrieval
alone still needs hybrid lexical retrieval and reranking. Full evidence is in
the [extended benchmark report](NCB_OPENTHAI_EXTENDED_RAG_BENCHMARK.md) and
machine-readable data in `../results/ncb/openthai_extended/results.json`.

## Live Open WebUI test: 8,192 context / 2,048 output

The final live run used the imported 73-file Knowledge Base, hybrid BM25
weight `0.65`, Qwen3-Embedding-4B, BAAI/bge-reranker-v2-m3, reranked top 3,
temperature `0`, and `enable_thinking=false`.

| Scenario | Expected | Retrieved top 3 | Prompt | Output | Finish | Retrieval | Chat |
|---|---|---|---:|---:|---|---:|---:|
| Access-log retention | 17 | 3, 17, 36 | 3,989 | 1,026 | stop | 18.21s | 52.32s |
| Correction/dispute | 25, 26, 27 | 27, 19, 26 | 2,876 | 580 | stop | 7.24s | 27.88s |
| Loan broker / credit model | 24/1, 24/2, 24/3 | 24/3, 3, 24/1 | 3,850 | 585 | stop | 19.88s | 42.08s |
| Adverse credit decision | 26, 27, 28 | 28, 24/4, 25 | 2,583 | 644 | stop | 5.67s | 29.35s |
| Unlawful disclosure | 20, 41 | 53, 51, 20 | 2,797 | 1,213 | stop | 11.12s | 57.36s |

- Mean retrieval / end-to-end chat time: `12.42s` / `41.80s`.
- Macro retrieval precision / recall: `46.7%` / `63.3%`.
- The largest observed prompt plus answer was 5,015 tokens, safely below the
  8,192-token context.
- In the preceding 1,024-token run every answer consumed exactly 1,024 tokens
  and ended mid-response. After raising the answer cap to 2,048 and disabling
  thinking, all five final responses ended with `finish_reason=stop`; actual
  answer sizes ranged from 580 to 1,213 tokens.
- The generation setting fixed answer truncation, but it did not improve
  retrieval coverage. Multi-section questions still require better candidate
  recall, query decomposition, metadata/section boosting, or a stronger
  reranker.

Full final answers and machine-readable evidence are in
[`openwebui_ncb_live_test_8192_2048_20260729/report.md`](../openwebui_ncb_live_test_8192_2048_20260729/report.md)
and `results.json` beside it. The deliberately constrained 1,024-token run is
retained in `openwebui_ncb_live_test_8192_20260729` as truncation evidence.

## Long-context test: 12,288 context / 4,096 output

The 12k test bypassed retrieval and injected exact structural sections so it
could isolate long-context synthesis from retrieval quality. Two evidence
packets required 9,113 and 9,698 actual prompt-plus-output tokens and therefore
could not have run with the same 4,096-token output reserve under the previous
8,192-token service.

| Scenario | Prompt | Output | Total | Finish | Citation P/R | Codex judge | Time |
|---|---:|---:|---:|---|---:|---:|---:|
| Integrated member IT audit | 5,915 | 3,783 | 9,698 | stop | 100%/100% | 2.0/5 | 130.35s |
| Loan broker / credit model | 5,023 | 4,090 | 9,113 | stop | 86%/86% | 2.5/5 | 133.52s |
| Unlawful disclosure incident | 3,999 | 1,816 | 5,815 | stop | 86%/100% | 2.0/5 | 57.00s |
| Criteria-first guardrail | 6,009 | 1,835 | 7,844 | stop | 88%/100% | 3.0/5 | 58.65s |

The expanded context solved capacity but not legal reliability. The answers
still introduced unsupported remediation deadlines, regulator-notification
duties, sample sizes, and legal effects. One answer ended mid-word even though
the API returned `finish_reason=stop`. A criteria-first prompt improved
coverage and concision, but still invented unlabeled sample values and due
dates. Citation-number metrics were high (`89.7%` precision / `96.4%` recall)
while substantive Codex judging averaged only `2.38/5`; this gap is why
citation matching alone is not a sufficient production quality gate.

Full answers, deterministic citation measurements, and judge findings are in
[`openthai_12k_long_context_20260729/report.md`](../openthai_12k_long_context_20260729/report.md)
with machine-readable `results.json` beside it.

## Practical production configuration

Do not use dense top-4 directly for this corpus. The controlled result supports this retrieval pipeline instead:

```text
query
  → Thai lexical/BM25 top 10 + Qwen embedding top 10
  → union and deduplicate by (law_name, section)
  → rerank the candidates
  → inject only the best 1–3 complete sections
  → OpenThai JSON answer + citation validator
```

For a question that clearly concerns loan brokers, boost/filter `หมวด ๓/๑`; for correction or adverse credit decisions, boost/filter `หมวด ๔`. Keep a whole `มาตรา` intact when injecting it. This follows the iApp recommendation to chunk statutes by section rather than arbitrary character windows.

Use “selection” regression tests before changing embeddings, chunking, or `top_k`: the model can obey the rule “cite only supplied sections” while still treating every supplied distractor as relevant. That distinction is the key control for NCB/legal RAG.
