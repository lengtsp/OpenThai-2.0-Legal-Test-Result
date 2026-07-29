# Codex judgement of the 36 outputs

This is a manual Codex review of the raw answers, performed after exact citation scoring. It is a quality-evaluation aid, **not legal advice or a legal opinion**. Scores use the 0–3 rubric in [methodology](methodology.md#codex-reviewer-rubric); `E/S/R` means Echo / Selection / retrieval top-5.

| Scenario | OpenThai E/S/R | Qwen E/S/R | Review notes |
|---|---:|---:|---|
| Consent for annual review (20) | 2 / 1 / 1 | 3 / 3 / 3 | Qwen identifies the scope issue in the old consent. OpenThai states the consent rule but does not address scope; it also adds irrelevant citations in Selection/RAG. |
| Cross-selling (20, 22) | 2 / 2 / 1 | 3 / 2 / 0 | Both are useful with supplied sections. Qwen's Selection answer adds an unnecessary civil-liability statement. Its RAG answer says the marketing use may be allowed with consent/model conditions, which is not a safe answer to the stated section-22 purpose/non-disclosure question. |
| Adverse lending notice (28) | 3 / 3 / 2 | 3 / 3 / 3 | Both explain written reasons, source, free check within 30 days and reconsideration. OpenThai's RAG adds 24/4 without using it. |
| Wrong data correction (19, 26) | 3 / 3 / 2 | 2 / 2 / 2 | OpenThai's RAG misses part of the section-26 route and adds 27. Qwen gives a sound operational answer but repeatedly cites only 26, omitting member-specific section 19. |
| Employee chat leak (24, 54) | 3 / 2 / 1 | 3 / 2 / 1 | Echo is strong for both. In Selection, Qwen adds unnecessary liability/prosecutor material. RAG retrieval misses 24/54 for both, leading to a wrong penalty route despite the general confidentiality conclusion. |
| Credit model (20/1) | 2 / 2 / 2 | 3 / 3 / 3 | OpenThai omits the statutory condition that only non-identifying data may be used. Qwen includes non-identification, consent and permitted purposes throughout. |

## Totals

| Model | Sum | Average | Reading of the result |
|---|---:|---:|---|
| OpenThai 2.0 Legal | 37 / 54 | 2.06 / 3 | Strong when exact evidence is supplied; loses precision when retrieval returns related but non-operative sections. |
| Qwen3.6-27B | 44 / 54 | 2.44 / 3 | More complete on consent scope and credit-model constraints, and faster in this run; still fails the employee-leak RAG case and makes an unsafe cross-selling conclusion when key section 22 is absent. |

## What this judgement does and does not say

- It says Qwen produced more useful answers in this fixed 6-scenario / 36-output run.
- It does **not** establish that Qwen is better for all Thai legal work, or that either model is safe to use without retrieval validation and professional review.
- The central system finding is shared by both models: a model cannot recover the correct section/penalty reliably when dense retrieval does not supply it. The RAG pipeline needs improvement before model-selection claims should drive production design.
