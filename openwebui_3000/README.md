# OpenThai Legal RAG Lab — Open WebUI

Configuration sources:

- [iApp OpenThai 2.0 Legal API documentation](https://iapp.co.th/docs/llm/openthai2p0-legal)
- [iApp Open WebUI and OpenThaiRAG tutorial](https://iapp.co.th/openmodels/openthai2p0-legal-rag-tutorial)

This deployment connects:

- Open WebUI `v0.9.5` at `http://127.0.0.1:3000`
- OpenThai 2.0 Legal OpenAI-compatible API at host port `3033`
- Qwen3-Embedding-4B OpenAI-compatible embedding API at host port `8082`
- Chroma persistence in the Docker volume `openthai-openwebui-data`

The legal corpus is prepared as one current consolidated section per clean text file under:

`../data/credit_info_act/openwebui_knowledge_v2/`

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
**Workspace → Knowledge** and upload the `credit-info-act-section-*.txt` files.

The deployment intentionally uses:

- one complete `มาตรา` per file in the iApp-trained
  `<law law_name="..." section="...">` scaffold;
- `CHUNK_SIZE=8000` with no overlap, so the longest active section (section 3,
  about 5,050 characters including the scaffold) remains one retrieval unit;
- page anchors, source URL, topic, and content hash in upload metadata rather
  than repeated in model context;
- amendment-note superscripts removed from effective law text using PDF
  font/layout evidence;
- Qwen3-Embedding-4B rather than Open WebUI's default local embedding;
- hybrid retrieval with BM25 weight `0.65`;
- enriched retrieval text disabled so YAML, filenames, and source URLs are not
  appended to the law text sent to the model;
- candidate top-k `12`, reranked to `8` with `BAAI/bge-reranker-v2-m3`.
  This is within iApp's documented `rag_top_k` maximum of 20 and was required
  for the NCB multi-section query to retain sections 25, 26, 27, and 28.
- relevance threshold `0.0`; retrieval is bounded by reranker top-8 instead of
  dropping all candidates when the reranker's score scale is below a generic
  cutoff.
- retrieval query expansion disabled: the original audit question is reranked
  once, avoiding three expensive CPU-reranker passes and keeping evaluation
  deterministic.
- the iApp-trained user scaffold: `Provided context:` followed by the retrieved
  `<law>` blocks and `Question (ตอบเป็นภาษาไทย):`.

OpenThai is currently served with a 12,288-token context in this test
environment. The documented JSON citation profile reserves up to 2,048 output
tokens and passes `enable_thinking=false`, so the answer budget is not consumed
by hidden reasoning. Do not increase reranked top-k or output length without
rechecking total prompt-token usage and GPU KV-cache capacity.

## iApp-recommended citation preset

The deployed custom model follows the documented trained JSON citation path:

```json
{
  "temperature": 0,
  "top_p": 1,
  "max_tokens": 2048,
  "min_tokens": 0,
  "frequency_penalty": 0,
  "presence_penalty": 0,
  "chat_template_kwargs": {
    "enable_thinking": false
  }
}
```

Its system prompt begins with iApp's exact OpenThaiGPT-Legal JSON citation
contract. It then adds a claim guardrail requiring actor, action, trigger, and
deadline verification and forbids invented subsection numbers. The user-side
RAG template uses the documented `Provided context` scaffold.

Import the supplied custom model into Open WebUI:

```bash
python3 openwebui_3000/import_balanced_model.py
```

Then select **OpenThai Legal RAG Citation (iApp Recommended)** and attach
**พ.ร.บ. ข้อมูลเครดิต — iApp structural v2**. The importer refreshes the model
registry so the preset is immediately available to chat routes.

Live checks through Open WebUI, with no client-side parameter overrides:

- access-log retention: valid JSON, section 17 only, correct two-year minimum,
  170 output tokens, `finish_reason=stop`, 33.97 seconds;
- adverse decision: valid JSON and only sections 28/26 after the claim
  guardrail, but the model still incorrectly transferred the 30-day
  data-subject exercise window into a bank-notification deadline.

The second result is a known model-synthesis failure, not a chunk-format or
output-budget failure. Production must reject a deadline claim unless a
claim-level validator finds the same actor, action, and trigger in the cited
text.

Do not set a large positive `min_tokens`. In the controlled test,
`min_tokens=4096` forced a 5,120-token response, ended with
`finish_reason=length`, repeated source URLs, and shifted heavily into English.
The complete parameter comparison, timings, full responses, and Codex judge
findings are in
[`../openthai_parameter_sweep_12k_20260729/report.md`](../openthai_parameter_sweep_12k_20260729/report.md).

The first start downloads the multilingual reranker (about 2.27 GB), so the
health endpoint remains unavailable until that one-time download completes.
Do not restart the container during this step.

## Security

Authentication is disabled and the port binds only to `127.0.0.1`. Do not change the binding to `0.0.0.0` unless authentication and access controls are configured first.
