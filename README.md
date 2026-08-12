# OpenThai 2.0 Legal: Thai Legal RAG Test with Ollama (Q4)

An independent RAG evaluation of
[OpenThai 2.0 Legal](https://huggingface.co/iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b)
running through Ollama Q4, compared with `Qwen3.6-35B-A3B` on llama.cpp Q5.

The tester is independent of the model developer. All results are **preliminary
and unreviewed**. They are not legal advice or a legal opinion. Any operational
use requires Thai legal-expert review of the current law, facts, and exceptions.

## Local test web application

The local `rag_webui_8083` application supports dataset selection, chat, and
dataset-table inspection.

- Select NitiBench, NCB, Digital Fraud, or the combined corpus.
- Inspect evidence source, score, page index, and parent/child provenance.
- Retain chat history and show dataset-specific test use cases.
- Open a dedicated dataset table without mixing it into the chat view.

## Datasets

| Dataset | Source | Tested corpus | Provenance |
|---|---|---:|---|
| NitiBench | [VISAI-AI/NitiBench](https://huggingface.co/datasets/VISAI-AI/nitibench) | 3,934 legal chunks | Passage embeddings contain statutory text only, never answers or reference answers. |
| Credit Information Business Act — **พระราชบัญญัติการประกอบธุรกิจข้อมูลเครดิต พ.ศ. ๒๕๔๕** | [BOT principal text, Updated-2559](https://www.bot.or.th/content/dam/bot/documents/th/laws-and-rules/laws-and-regulations/legal-department/7-ncb-act/7-1-ncb-act/7.1.2-Law_TH_CreditBureau%20Updated-2559.pdf) | 225 units: 73 parent + 152 child | The active corpus is one consolidated amendments 1–6 collection; an amendment-only PDF is not a separate dataset. |
| Digital Fraud Management | [BOT Policy Guideline 2568/0254](https://www.bot.or.th/content/dam/bot/fipcs/documents/FPG/2568/ThaiPDF/25680254.pdf) | 54 units | Split by **ข้อ** (clause) and subclause with page provenance. |

The BOT NCB principal document marked `Updated-2559` is consolidated through
2559 and does not include the sixth amendment from 2565. It is therefore used
as a cross-check, not as a replacement for the active full amendments 1–6
corpus. Cross-checking **มาตรา** (section) 20, 26–28, and 51 confirms the
substantive rules used in the five NCB cases. The full 1–6 version adds a
reference to section 24/1 in the scope of section 51, but the maximum penalty
does not change.

## Test design

The test uses 15 fixed questions: five per dataset. Both models receive the
same evidence packet, isolating answer synthesis and citation behavior after
retrieval.

```text
Question
  ├─ Dense retrieval: Qwen3-Embedding-4B, 2,560 dimensions, L2-normalized
  ├─ Sparse retrieval: lexical / Thai n-gram retrieval
  └─ Hybrid fusion + reranking
                 ↓
       same top_k = 8 evidence packet
                 ↓
    OpenThai Q4       Qwen3.6-35B-A3B Q5
                 ↓
      JSON answer + grounded citations
                 ↓
   score expected citations only after inference
```

Expected citations, reference answers, and scoring labels are never passed to
the embedding model, retriever, reranker, or generation prompt. They are used
only after the answer is returned.

| Parameter | Value |
|---|---:|
| Retrieval `top_k` | 8 |
| Embedding model | Qwen3-Embedding-4B, 2,560 dimensions |
| Temperature / top_p | 0.0 / 1.0 |
| Maximum output tokens | 2,048 |
| Seed | 42 |
| Output contract | JSON answer + citations |

## Results: three datasets × five questions

The run completed all 15 cases. Retrieval found the expected citation in the
top 8 for every case, and both models produced parseable JSON in all 15 cases.

| Dataset | Expected-citation recall: OpenThai / Qwen | Codex Sol source-grounded review: OpenThai / Qwen | Mean end-to-end time: OpenThai / Qwen |
|---|---:|---:|---:|
| NitiBench | 100% / 100% | 4 supported + 1 partial / 5 supported | 21.73s / 10.69s |
| NCB full amendments 1–6 | 100% / 100% | 3 supported + 2 partial / 5 supported | 18.85s / 7.70s |
| Digital Fraud | 70% / 100% | 3 supported + 2 partial / 5 supported | 21.18s / 8.83s |
| **All 15 cases** | **90% / 100%** | **10 supported + 5 partial / 15 supported** | **20.58s / 9.07s** |

Codex Sol read the 30 actual answers against the admitted source text,
independently of automated metrics. This identifies meaningful errors that a
grounded-citation flag can miss, including wrong actors, omitted conditions,
and citations to adjacent provisions.

> Times are sequential, single-machine observations. They are neither a
> production-latency guarantee nor a concurrency benchmark.

<details>
<summary>Per-case test list, outcomes, and review boundary — questions, answers, and full result detail are intentionally hidden</summary>

| Dataset | Case | Expected citation | OpenThai: citation / review | Qwen: citation / review |
|---|---|---|---|---|
| NitiBench | unlicensed futures market | 132 | 1.00 / supported | 1.00 / supported |
| NitiBench | orchard lease | 565 | 1.00 / supported | 1.00 / supported |
| NitiBench | minor adoption | 1598/26 | 1.00 / partially supported | 1.00 / supported |
| NitiBench | current account | 856 | 1.00 / supported | 1.00 / supported |
| NitiBench | limited-company shareholder | 1096 | 1.00 / supported | 1.00 / supported |
| NCB | owner dispute | 27 | 1.00 / partially supported | 1.00 / supported |
| NCB | disclosure consent | 20 | 1.00 / supported; over-citation noted | 1.00 / supported |
| NCB | correction deadline | 26 | 1.00 / supported | 1.00 / supported |
| NCB | rejection reasons | 28 | 1.00 / partially supported | 1.00 / supported |
| NCB | unlawful disclosure penalty | 51 | 1.00 / supported | 1.00 / supported |
| Digital Fraud | scope | 4 | 1.00 / supported; over-citation noted | 1.00 / supported |
| Digital Fraud | governance | 5.3.1, 5.3.1(2) | 0.50 / partially supported | 1.00 / supported |
| Digital Fraud | monitoring | 5.3.2(2), 5.3.2(2.1) | 0.50 / supported | 1.00 / supported |
| Digital Fraud | customer response | 5.3.2(4.2), 5.3.2(4.3) | 0.50 / partially supported | 1.00 / supported |
| Digital Fraud | reporting | 5.3.5 | 1.00 / supported | 1.00 / supported |

`supported` means the material answer claims follow from the source text in
the benchmark. `partially supported` means the core is grounded but a material
actor, condition, scope, or required part is missing or wrong. No answer was
classified as unsupported in this run.

</details>

## Why a correct citation can still yield an incomplete answer

OpenThai retrieved relevant evidence successfully, but the partially supported
answers exhibited these failure modes:

- confusing the party with a duty and the party with a right of appeal;
- changing the frequency or modality of a requirement;
- answering one limb of a multi-part question while omitting another; and
- citing adjacent provisions even where one direct provision is sufficient.

Retrieval and citation metrics must therefore be reported separately from
source-grounded answer review.

## Supplementary baseline: PostgreSQL and Milvus

<details>
<summary>NitiBench five-case retrieval-backend baseline</summary>

| Metric | PostgreSQL hybrid RRF | Milvus native BM25 + RRF |
|---|---:|---:|
| Candidate recall@20 | 100% | 100% |
| Citation recall / precision | 100% / 100% | 100% / 100% |
| Exact citation set | 5/5 | 5/5 |
| Mean retrieval time | 1.630s | 0.057s |
| Mean end-to-end time | 9.156s | 7.280s |

PostgreSQL uses dense pgvector + FTS/pg_trgm + application RRF (`k=60`).
Milvus uses dense cosine + Thai 3/4-character n-gram BM25 + native RRF
(`k=80`). These timings come from different runs and cache states, so they are
exploratory only and do not guarantee production performance.

</details>

## Limitations and human-review boundary

- This is a fixed 15-question benchmark, not a random sample or a measure of
  coverage across Thai law.
- An exact expected citation does not establish complete legal correctness.
- Codex Sol is an independent model review, not Thai legal-expert adjudication.
- Multi-section questions, exceptions, and real factual scenarios require more
  testing before operational use.
- This repository does not contain model weights, credentials, access tokens,
  or chat sessions.
