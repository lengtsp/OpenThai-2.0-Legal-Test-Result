# Codex Sol evaluation — wide-context legal RAG, three datasets

Status: **complete for the approved two-runtime comparison**. OpenThai vLLM BF16 and Qwen3.6-35B-A3B Q5 are complete.

This is a preliminary, unreviewed review of generated text against the evidence actually supplied. It is not legal advice or Thai legal-expert adjudication.

## Controlled comparison

| Control | Value |
|---|---|
| common input | `generation_input.json`; 15 questions, eight evidence rows each, no labels or answers |
| system prompt | identical across all cases/runtimes; SHA-256 `32b66676fcb8f90dccc28152cc1424dcdbed32c0949e33751720c5fd277097a0` |
| generation | temperature 0, top_p 1, max_tokens 2,048, seed 42, thinking disabled |
| answer contract | JSON answer and source-grounded citations |
| scoring | expected sections are loaded only after generation |

Thus the **prompt instruction is the same** for BF16 and Qwen Q5. The per-case user message/evidence is also identical across both models. Only the required API transport differs: vLLM JSON mode and llama.cpp OpenAI-compatible chat.

## Dataset and retrieval boundary

| Dataset | Citation child | Parent structure | Current corpus |
|---|---|---|---|
| NitiBench | statutory section | source-law structure | frozen label-free hybrid packet |
| NCB | primary `มาตรา` | 9 chapters | 66 official article children from BOT PDF pp.1–18; footer removed |
| Digital Fraud | primary `ข้อ X.X` | 6 main topics | 11 X.X children from BOT PDF pp.2–13; nested X.X.X text is grouped under owning X.X and may not be cited separately |

NCB and NitiBench are article-oriented. Digital Fraud is a non-statute notice with integrated nested requirements; a long `5.3` packet is expected and was not truncated. All five Digital Fraud prompts are about 26.7k characters and complete grouped `5.3.1`–`5.3.6` content reached the model.

NitiBench uses its frozen hybrid evidence. NCB and Digital Fraud use a documented Thai lexical plus character 3/4-gram fallback because the embedding service was unavailable while BF16 used the GPU. The latter two are therefore a wide-context generation comparison, **not** a new hybrid-retrieval claim.

## Automatic scores after inference

| Dataset / 5 cases | Runtime | JSON | grounded citations | expected recall | citation precision | mean answer time |
|---|---|---:|---:|---:|---:|---:|
| NitiBench | OpenThai vLLM BF16 | 5/5 | 5/5 | 1.00 | 1.00 | 0.8820 s |
| NitiBench | Qwen3.6 35B-A3B Q5 | 5/5 | 5/5 | 1.00 | 1.00 | 1.3370 s |
| NCB | OpenThai vLLM BF16 | 5/5 | 5/5 | 0.80 | 1.00 | 1.3014 s |
| NCB | Qwen3.6 35B-A3B Q5 | 5/5 | 5/5 | 1.00 | 1.00 | 2.7195 s |
| Digital Fraud | OpenThai vLLM BF16 | 5/5 | 4/5 | 0.40 | 0.80 | 2.5440 s |
| Digital Fraud | Qwen3.6 35B-A3B Q5 | 5/5 | 3/5 | 0.40 | 0.60 | 3.1433 s |

The expected recall/precision diagnostics are post-inference only. They do not establish a complete or controlling legal answer.

## Codex Sol text review

| Case group | OpenThai BF16 | Qwen Q5 | Finding |
|---|---|---|---|
| NitiBench 5 cases | pass 5/5 | pass 5/5 | Both accurately retain the operative statutory rule and expected citation. |
| NCB owner dispute, consent, rejection | pass 3/3 | pass 3/3 | Actor, action, conditions, written notice, and 30-day right are retained. |
| NCB correction deadline | partial | pass | BF16 says only “within 30 days,” omitting the duty bearer/action. Qwen makes the answer self-contained. |
| NCB unlawful-disclosure penalty | needs correction | pass | BF16 cites civil liability under section 41 rather than the requested criminal penalty under 51. Qwen distinguishes both effects and cites 41 plus 51. |
| Digital Fraud scope | evidence-limited | evidence-limited | Lexical candidate top-8 omitted scope rows 4.1–4.3. This is candidate admission, not context truncation or a model-quality ranking. |
| Digital Fraud governance | pass | pass | Complete grouped 5.3 evidence supports both answers. |
| Digital Fraud monitoring | pass | partial | Qwen text is supported by 5.3 but writes forbidden granular citation `5.3.2 (2)`. |
| Digital Fraud customer response | partial | pass | BF16 content is supported by 5.3 but cites forbidden `5.3.3`; Qwen cites the owning 5.3 block. |
| Digital Fraud reporting | partial | partial | Content conveys reporting duty, but BF16 cites 5.2 and Qwen cites forbidden 5.3.5 instead of permitted owner block 5.3. |

| Runtime | pass | partial | needs correction | evidence-limited |
|---|---:|---:|---:|---:|
| OpenThai vLLM BF16 | 10 | 3 | 1 | 1 |
| Qwen3.6 35B-A3B Q5 | 12 | 2 | 0 | 1 |

### NCB differences: shared evidence audit

Qwen did **not** receive additional retrieved evidence in either difference below.  For each
case, the prompt messages and ordered top-8 rows were identical between BF16 and Qwen.
The scorer's expected section for the penalty case is independently set to 51 after inference.
Codex Sol's separate reading is that 51 is material to answering the word “penalty” directly,
whereas 41 describes civil compensation; this is a preliminary model review, not legal-expert
adjudication.

| Case | Shared top-8 sections | BF16 result | Qwen result | Evidence-based conclusion |
|---|---|---|---|---|
| correction deadline | `26, 19, 25, 17, 48, 20, 3, 27` | “within 30 days from request” / cite 26 | company or member must notify the examination/correction result with reasons within 30 days / cite 26 | Section 26 alone supplies all material detail. Qwen retains actor, action, reason, and timing; it did not get extra context. |
| unlawful-disclosure penalty | `41, 17, 3, 51, 61, 20, 24, 22` | civil damages / cite 41 | civil damages under 41 plus imprisonment up to 3 years, fine up to 300,000 baht, or both under 51 / cite 41, 51 | Both 41 and 51 were already supplied. Qwen is broader but grounded; BF16 does not state the criminal sanction that the scorer expects for the wording of this test question. |

## Practical use and caution

1. Enforce the Digital Fraud citation vocabulary as X.X only; validator must reject X.X.X even when the answer text uses grouped evidence correctly.
2. Add a candidate-admission gate: for a scope question, retrieve a scope provision before returning a definitive answer. Otherwise say evidence is insufficient or retrieve again.
3. Before final answer, use a generic coverage check for duty bearer/right holder, action/right, material condition/exception, and deadline/written-notice requirement. This is label-free and corrects over-short answers such as “30 days.”
4. Use NCB top-1 only behind a measured high-confidence gate; a global top-1 policy would lose legitimate multi-provision context.
5. Restore embeddings and hybrid retrieval before using NCB/BOT candidate scores as retriever performance claims.

- Fixed 15 cases are not a coverage estimate.
- Valid JSON and an in-context citation do not prove the controlling legal provision.
- Results remain preliminary/unreviewed and require Thai legal-expert review.
- Sequential timings are not production latency claims.

## Audit artifacts

The immutable label-free input, raw generation JSON, and post-inference score JSON are retained
in the local benchmark run directory
`runs/expanded_context_3datasets_20260813_082922/`.  They are not copied into this publication
repository, so the public report does not create broken links or expose full prompt packets.
The reported values above are calculated from:

- `generation_input.json`
- `generation_vllm_bf16.json` and `scored_vllm_bf16.json`
- `generation_qwen_q5.json` and `scored_qwen_q5.json`
