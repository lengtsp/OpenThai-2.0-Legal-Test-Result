# OpenThai 2.0 Legal — Test Results and Local RAG Web UI

This repository contains reproducible local test artefacts for `iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b`:

- a dependency-light RAG web UI that calls an OpenAI-compatible vLLM service;
- a small, page-source-preserved Bank of Thailand (BOT) corpus for evaluation;
- inference, RAG, groundedness, and session-persistence reports.

No model weights, API tokens, database credentials, or chat-session contents are included.

## Contents

- `web/rag_webui_8083/` — browser UI and Python service on port `8083`
- `web/rag_webui_8083/data/legal_corpus.json` — five BOT evaluation chunks with source URLs
- `reports/BOT_RAG_EVALUATION_20260729.md` — eight BOT-grounded test scenarios and findings
- `reports/INFERENCE_RAG_TEST_REPORT.md` — initial model/inference measurements
- `reports/RAG_WEBUI_8083.md` — architecture and API notes

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
