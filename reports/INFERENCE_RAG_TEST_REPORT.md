# OpenThai 2.0 Legal — Local Inference and RAG Test Report

**Test date:** 2026-07-29 (Asia/Bangkok)  
**Model:** `iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b`  
**Endpoint tested:** `http://127.0.0.1:8000/v1/chat/completions`

## Executive summary

The local vLLM server successfully generated Thai legal answers and valid JSON in all four requests. In the focused RAG test, it selected and cited Civil and Commercial Code section 420 exactly. In the distractor test, it cited the correct section **and** an irrelevant Criminal Code section 328, so retrieval/context discipline remains essential.

The running test configuration uses FlashAttention 2 for attention, Triton for MoE, and the native vLLM sampler. These choices work around a FlashInfer/Ninja JIT failure caused by the existing vLLM environment path containing spaces. They are a stability workaround, not a throughput benchmark configuration.

## Sources studied

1. [Hugging Face model card](https://huggingface.co/iapp/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b)
   - BF16 model with 17 shards; 30B MoE with about 3B active parameters.
   - Recommended served context is 32,768 tokens. The card reports vLLM verification on H100 with `--trust-remote-code` and `--gpu-memory-utilization 0.90`.
   - The model is trained for a JSON citation contract: cite only the legal sections supplied in the context.
2. [iApp OpenAI-compatible API documentation](https://iapp.co.th/docs/llm/openthai2p0-legal)
   - Hosted endpoint: `https://api.iapp.co.th/v3/llm/openthai2p0-legal/chat/completions`.
   - Hosted API defaults to server-side RAG over 39 Thai laws / 6,300 sections, and returns `retrieved_documents` for audit.
   - `rag_inject: "user"` is the documented choice for JSON citations; `rag_inject: "system"` suits longer legal prose.
3. [Open WebUI / OpenThaiRAG tutorial](https://iapp.co.th/openmodels/openthai2p0-legal-rag-tutorial)
   - For self-hosting, chunk statutes by **section (มาตรา)**, preserving `law_name` and `section` metadata.
   - Open WebUI is the quick UI path; OpenThaiRAG provides a Thai-oriented Milvus + BGE-M3 RAG stack.
   - Retrieval quality determines citation quality; legal output remains decision support and needs human verification.

## Local server configuration used for the tests

| Item | Value |
| --- | --- |
| GPU | NVIDIA RTX PRO 6000 Blackwell Workstation Edition (96 GB) |
| vLLM | 0.25.1 |
| Precision | BF16 |
| Served context in this test | 4,096 tokens |
| GPU memory utilization | 0.80 |
| Attention backend | FlashAttention 2 |
| MoE backend | Triton |
| Sampler | Native vLLM / PyTorch path |
| Thinking | Off except the explicit comparison test |

The model loaded in about 58.93 GiB and the server reported 15.44 GiB available for KV cache. This is a **functional test configuration**. The model-card 32k context configuration has not yet been benchmarked on this machine.

### Stable launch command used

```bash
VLLM_PLUGINS='' VLLM_USE_FLASHINFER_SAMPLER=0 \
  /home/indows-11/my_code/model/venvs/vllm_025/bin/vllm serve \
  /home/indows-11/my_code/model/openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b \
  --served-model-name openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b \
  --tensor-parallel-size 1 \
  --trust-remote-code \
  --max-model-len 4096 \
  --max-num-batched-tokens 2048 \
  --gpu-memory-utilization 0.80 \
  --enforce-eager \
  --moe-backend triton \
  --host 127.0.0.1 --port 8000
```

`VLLM_USE_FLASHINFER_SAMPLER=0` disables only FlashInfer top-k/top-p sampling. It does **not** disable FlashAttention 2. `--moe-backend triton` avoids FlashInfer's CUTLASS MoE JIT path. Both are needed here because FlashInfer 0.6.13 generated Ninja rules containing the venv path with spaces and failed before the API could start.

## Test method

- Requests used the OpenAI-compatible `/v1/chat/completions` route.
- `temperature: 0`, `top_p: 1`, `max_tokens: 1536`.
- RAG tests supplied section-level text directly in the prompt, the self-hosted equivalent of a retriever's output.
- `chat_template_kwargs: {"enable_thinking": false}` was used for citation tests.
- Latency is client-observed end-to-end time after the server was warm. The approximate token rate is `completion_tokens / latency`; it includes request overhead and is not a formal decode benchmark.

## Results

| Test | Prompt / expected behavior | Result | Latency | Tokens (prompt / completion) | Approx. completion tokens/s |
| --- | --- | --- | ---: | ---: | ---: |
| `rag_echo_420` | Only Civil and Commercial Code §420 supplied; cite §420 | Valid JSON; cited §420 only | 2.645 s | 321 / 74 | 28.0 |
| `rag_selection_420_vs_328` | §420 plus irrelevant Criminal Code §328; cite §420 only | Valid JSON; cited §420 **and** irrelevant §328 | 3.536 s | 405 / 124 | 35.1 |
| `closed_book_night_theft` | No context; ask the night-theft section | Valid JSON; answered Criminal Code §335 | 2.291 s | 83 / 74 | 32.3 |
| `rag_echo_420_thinking_on` | Same focused §420 RAG test, thinking enabled | Final JSON cited §420 only | 7.070 s | 317 / 255 | 36.1* |

\*The thinking-on completion count includes internal reasoning tokens, so it is not directly comparable to the thinking-off user-visible completion rate.

### Citation quality for the two controlled RAG tests

| Test | Expected set | Returned set | Precision | Recall | F1 |
| --- | --- | --- | ---: | ---: | ---: |
| Echo | `{ป.พ.พ. 420}` | `{ป.พ.พ. 420}` | 1.00 | 1.00 | 1.00 |
| Selection | `{ป.พ.พ. 420}` | `{ป.พ.พ. 420, ป.อาญา 328}` | 0.50 | 1.00 | 0.67 |

The selection result is the key finding: the prompt said to cite only applicable supplied sections, but the model retained the distractor citation. Do not treat the JSON schema alone as a guarantee of citation precision.

### Thinking comparison

For the same focused §420 question, thinking-on used 255 completion tokens and took 7.070 s, versus 74 completion tokens and 2.645 s with thinking-off. For a simple citation response, thinking-off was faster and still returned the correct single citation. Reserve thinking for complex analysis or essay drafting, as the documentation recommends.

## Recommended self-hosted RAG design

1. Extract current statutory text from an authoritative source and keep one **มาตรา** per retrieval chunk.
2. Store at least `law_name`, `section`, source URL/version, and effective-date metadata with every chunk.
3. Retrieve a focused candidate set, then rerank. Start with a small `top_k`; do not stuff unrelated law sections into the prompt.
4. Use the JSON citation contract for automation, then validate that every output citation is in the retrieved set and, where possible, that it is one of the accepted/reranked sections.
5. Display the retrieved text and citations to the reviewer. Verify against the current statute before any legal reliance.
6. Evaluate end-to-end with NitiBench or a held-out, page/section-grounded internal set. Measure retrieval recall separately from citation precision.

## Local API request example

When sending raw JSON to the local vLLM server, `chat_template_kwargs` belongs at the top level of the request. (`extra_body` is an OpenAI Python SDK convenience wrapper; it should not be nested inside raw JSON.)

```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "openthai2.0-legal-thaillm-nemotron-3-nano-30b-a3b",
    "messages": [
      {"role": "system", "content": "ตอบเป็นภาษาไทยอย่างกระชับ"},
      {"role": "user", "content": "ประเทศไทยมีเมืองหลวงชื่ออะไร"}
    ],
    "temperature": 0,
    "max_tokens": 256,
    "chat_template_kwargs": {"enable_thinking": false}
  }'
```

## Scope and next steps

- The hosted iApp RAG API was studied from its documentation but not called because no iApp API key was supplied for this test.
- Local results validate inference and prompt-based RAG behavior; they do not validate legal correctness against the current statute database.
- Before production use, benchmark the final 32k serving configuration, build a section-level corpus, and add citation precision checks to the RAG pipeline.
