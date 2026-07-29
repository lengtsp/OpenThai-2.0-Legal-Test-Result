# OpenThai Legal RAG Lab — Open WebUI

This deployment connects:

- Open WebUI `v0.9.5` at `http://127.0.0.1:3000`
- OpenThai 2.0 Legal OpenAI-compatible API at host port `3033`
- Qwen3-Embedding-4B OpenAI-compatible embedding API at host port `8082`
- Chroma persistence in the Docker volume `openthai-openwebui-data`

The legal corpus is prepared as one current consolidated section per Markdown file under:

`../data/credit_info_act/openwebui_knowledge/`

## Start

On this machine Docker Desktop is reachable through `docker.exe`:

```bash
docker.exe compose -f openwebui_3000/docker-compose.yml up -d
```

On a Linux host with a mounted Docker socket:

```bash
docker compose -f openwebui_3000/docker-compose.yml up -d
```

Verify:

```bash
curl http://127.0.0.1:3000/health
curl http://127.0.0.1:3000/api/models
```

## Knowledge configuration

Import the prepared 73 files through the normal Open WebUI APIs:

```bash
python3 openwebui_3000/import_ncb_knowledge.py
```

The importer signs into the loopback-only no-auth lab user, creates or reuses
the Knowledge Base, processes missing files synchronously, and runs one batch
ingest into the Knowledge collection. You can also create the Knowledge Base manually under
**Workspace → Knowledge** and upload the `credit-info-act-section-*.md` files.

The deployment intentionally uses:

- section-sized chunks (`CHUNK_SIZE=4000`, no overlap);
- no Markdown-header re-splitting: each prepared section file remains one
  retrieval unit;
- Qwen3-Embedding-4B rather than Open WebUI's default local embedding;
- hybrid retrieval with BM25 weight `0.65`;
- enriched filename/section metadata;
- candidate top-k `8`, reranked to `3` with `BAAI/bge-reranker-v2-m3`.
- relevance threshold `0.0`; retrieval is bounded by reranker top-3 instead of
  dropping all candidates when the reranker's score scale is below a generic
  cutoff.
- retrieval query expansion disabled: the original audit question is reranked
  once, avoiding three expensive CPU-reranker passes and keeping evaluation
  deterministic.
- a strict user-injected legal RAG template that forbids unsupported
  closed-book conclusions and asks for exact section plus Open WebUI source
  markers.

OpenThai is served with an 8,192-token context in this test environment. The
live benchmark reserves up to 2,048 tokens for a broader audit answer and
passes `enable_thinking=false` so the answer budget is not consumed by hidden
reasoning. Do not
increase reranked top-k or output length without rechecking total prompt-token
usage and GPU KV-cache capacity.

The first start downloads the multilingual reranker (about 2.27 GB), so the
health endpoint remains unavailable until that one-time download completes.
Do not restart the container during this step.

## Security

Authentication is disabled and the port binds only to `127.0.0.1`. Do not change the binding to `0.0.0.0` unless authentication and access controls are configured first.
