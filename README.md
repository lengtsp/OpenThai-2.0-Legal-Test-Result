# OpenThai 2.0 Legal — Test Results and Local RAG Web UI

This repository contains reproducible local test artefacts for `iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b`:

- a dependency-light RAG web UI that calls an OpenAI-compatible vLLM service;
- a small, page-source-preserved Bank of Thailand (BOT) corpus for evaluation;
- inference, RAG, groundedness, and session-persistence reports.

No model weights, API tokens, database credentials, or chat-session contents are included.

## NCSA page-grounded RAG benchmark — OpenThai2.0 vs Qwen3.6-27B

This evaluation replays the same 10 Thai IT-internal-audit scenarios against a 629-page NCSA cyber-security compendium. Both models received the same fixed prompt, the same top-3 BM25 evidence packet, and the same 1,497 PyMuPDF recursive chunks. Codex reviewed each answer against its selected source chunks.

| Metric | OpenThai2.0 Legal | Qwen3.6-27B | Outcome |
|---|---:|---:|---|
| Mean model-request latency | 23.96 s | **21.77 s** | Qwen faster by **9.1%** |
| Strict `[p.x c.y]` citation syntax | 5/10 | **10/10** | Qwen stronger |
| Codex evidence-grounded judge score | 7.85/10 | **9.20/10** | Qwen stronger |

The comparison is an operational RAG replay rather than a pure model-quality study: OpenThai used vLLM and Qwen used llama.cpp with a Q8 GGUF build. Model loading is excluded from the latency metrics. The detailed method, per-scenario results, limitations, and judge rubric are in [the NCSA benchmark report](reports/NCSA_OPENTHAI_VS_QWEN36_27B_BENCHMARK.md).

### Scenario captures

Each capture is produced from the saved test outputs; it shows the Thai question, retrieved page/chunk evidence, model latency, citation state, Qwen answer excerpt, and Codex judge note.

<details>
<summary>Scenario 1 — CII scope</summary>

![Scenario 1 — CII scope](captures/scenario-01-cii-scope.png)
</details>

<details>
<summary>Scenario 2 — Governance</summary>

![Scenario 2 — Governance](captures/scenario-02-governance.png)
</details>

<details>
<summary>Scenario 3 — Risk assessment</summary>

![Scenario 3 — Risk assessment](captures/scenario-03-risk-assessment.png)
</details>

<details>
<summary>Scenario 4 — Monitoring</summary>

![Scenario 4 — Monitoring](captures/scenario-04-monitoring.png)
</details>

<details>
<summary>Scenario 5 — Incident response</summary>

![Scenario 5 — Incident response](captures/scenario-05-incident-response.png)
</details>

<details>
<summary>Scenario 6 — Incident reporting</summary>

![Scenario 6 — Incident reporting](captures/scenario-06-incident-reporting.png)
</details>

<details>
<summary>Scenario 7 — Cloud and third party</summary>

![Scenario 7 — Cloud and third party](captures/scenario-07-cloud-and-third-party.png)
</details>

<details>
<summary>Scenario 8 — Configuration</summary>

![Scenario 8 — Configuration](captures/scenario-08-configuration.png)
</details>

<details>
<summary>Scenario 9 — Awareness</summary>

![Scenario 9 — Awareness](captures/scenario-09-awareness.png)
</details>

<details>
<summary>Scenario 10 — Risk-proportional conclusion</summary>

![Scenario 10 — Risk-proportional conclusion](captures/scenario-10-risk-proportional-conclusion.png)
</details>

## Contents

- `web/rag_webui_8083/` — browser UI and Python service on port `8083`
- `web/rag_webui_8083/data/legal_corpus.json` — five BOT evaluation chunks with source URLs
- `reports/BOT_RAG_EVALUATION_20260729.md` — eight BOT-grounded test scenarios and findings
- `reports/INFERENCE_RAG_TEST_REPORT.md` — initial model/inference measurements
- `reports/RAG_WEBUI_8083.md` — architecture and API notes
- `reports/NCSA_OPENTHAI_VS_QWEN36_27B_BENCHMARK.md` — NCSA recursive-chunk replay, latency comparison, and Codex judge rubric
- `captures/` — 10 rendered scenario captures generated from saved benchmark JSON
- `tools/generate_scenario_captures.js` — reproducible capture renderer

## Run locally

Start an OpenAI-compatible vLLM server first. The example UI expects it at `127.0.0.1:3033` and uses the served model name `openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b`.

The RAG UI persists chat sessions in PostgreSQL. Create a database named `opengpt` and set its connection values only in your shell or deployment secret store:

```bash
export OPENGPT_DB_HOST=127.0.0.1
export OPENGPT_DB_PORT=5432
export OPENGPT_DB_NAME=opengpt
export OPENGPT_DB_USER='your_user'
export OPENGPT_DB_PASSWORD='your_password'
python3 web/rag_webui_8083/server.py
```

Open `http://localhost:8083`.

The service needs Python `psycopg2` for PostgreSQL session persistence. It has no frontend build step.

## BOT source boundary

The corpus is a small evaluation set, not a complete legal/regulatory database. Verify any answer against the linked primary source and current official notices. See the BOT evaluation report for observed limitations, especially citation compliance in synthesis answers.
