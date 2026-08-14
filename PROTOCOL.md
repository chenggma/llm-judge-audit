# Judge Audit — Pre-Registered Protocol

**Status: FROZEN before data collection.** This file specifies the full
experiment matrix, metrics, and decision criteria *before* any responses are
generated or judged. Results are written afterward in `REPORT.md`. Deviations,
if any, will be logged in `PROTOCOL_DEVIATIONS.md` with reasons — not silently
edited here. The git history of this file is the audit trail.

Date frozen: 2026-08-14

---

## 1. Research question

LLM-as-judge is the de-facto evaluation method for instruction-following
quality, yet the judges themselves are rarely audited. We measure, for judges
across a price spectrum:

1. Accuracy against programmatic ground truth (hard constraints, planted
   violations, known-dominance pairs — see §4)
2. Position bias (pairwise mode)
3. Length bias (controlling for measured quality)
4. Self-preference (judge favoring same-family outputs, quality-controlled)
5. Confidence calibration (does stated/derived confidence predict correctness?)
6. Stability (noise floor under resampling; sensitivity to rubric paraphrase)

and answer the engineering question: **given a budget, what mix of cheap
judge / strong judge maximizes accuracy per dollar?**

## 2. Task domain

Instruction-following quality. Each item is a multi-constraint instruction
(4–6 explicit constraints) paired with a model response. Constraints are of
two kinds, *by design*:

- **HARD** — mechanically verifiable (word counts, required sections, format,
  forbidden terms). Verified by `src/verify_hard.py`; provides *programmatic
  ground truth inside the subjective task*, an internal anchor for both human
  and judge error.
- **SOFT** — requires judgment (completeness of an explanation, tone,
  faithfulness to a scenario, quality of an argument). This is the part that
  actually needs a judge.

Target mix per item: 2–3 HARD + 2–3 SOFT.

## 3. Materials

- **Instructions**: ~180 authored for this study (schema and taxonomy in
  `data/instructions/`; taxonomy: format / content-coverage / exclusion /
  style-tone / audience / reasoning-structure). Seeds inspired by public
  benchmarks (IFEval-style verifiable constraints) but written fresh to avoid
  train-set contamination of judges.
- **Responses**: each instruction answered by a capability ladder of
  generator models (small local ≈3B, mid-tier, frontier), plus a
  **constructed-violation arm**: the mid-tier response with ≥2 hard
  constraint violations planted mechanically (`src/degrade.py`, seeded per
  instruction; planted constraint ids recorded). Prompt-based degradation
  was tried first and rejected — aligned models would not comply (0
  violations in both attempts; see git history). The mechanical arm both
  populates the low end of the quality range and provides
  known-by-construction negative labels for judge-sensitivity measurement.
- **Judging coverage**: all (instruction, response) units (~720), in a
  committed seeded shuffle (`scripts/sample_gold.py`); the shuffle order
  defines the pre-registered stability subset (first 100).

## 4. Ground truth (design v2 — changed before freeze, see log below)

**Design change (2026-08-14, pre-freeze):** v1 planned human gold labels
(450 items, single annotator with reliability checks). The annotator's time
turned out not to be available. Rather than substitute LLM labels and call
them human — which would misrepresent provenance — the audit is re-anchored
on ground truth that requires no human labeling and is *stronger* where it
applies:

- **Programmatic truth on HARD constraints** (`src/verify_hard.py`):
  deterministic verdicts on ~2–3 constraints per item across all arms.
- **Planted violations** (`src/degrade.py`): the constructed arm carries
  verified-failing constraint ids; judge miss rates are exactly measurable.
- **Known-dominance pairs**: every (mid, degraded-of-that-same-mid) pair has
  a known correct preference — degraded is the same response with planted
  violations, strictly worse by construction. ~180 pairwise items with
  ground-truth answers, used for pairwise accuracy AND position bias.
- **SOFT constraints carry no truth claim**: judge-vs-judge cross-agreement
  is reported descriptively, labeled as such.
- **Optional human mini-set** (if annotator time appears): ~100 items under
  `docs/ANNOTATION_GUIDE.md`, reported as a secondary human anchor. Runs
  under the original guide; κ gate 0.60 applies to its intra-rater retest.
- **Disclosed LLM-annotator arm (optional)**: a frontier assistant model may
  annotate the same items as a *disclosed, audited reference judge* — scored
  against programmatic truth like every other judge, never presented as
  human.

## 5. Judges under audit

4 API judges spanning a ~4× blended per-judgment price range (models fixed
in `src/config.py`; chosen among current frontier, mid, cheap tiers, plus one
open-weights model if API access is practical), each in 2 elicitation modes:

- **Rubric mode**: judge sees instruction + response + the constraint list,
  returns per-constraint verdicts + holistic 1–5 + confidence 0–100.
- **Bare mode**: judge sees instruction + response only, returns holistic
  1–5 + confidence (no constraint list) — measures how much of judge skill
  is really rubric-following.

Pairwise mode (for position bias): rubric-style prompt, both orders (A-B,
B-A) for every pair.

**Zero-budget execution note (fixed before freeze):** all calls run on
providers' free tiers (Mistral La Plateforme, Groq, local Ollama); the cost
axis of every cost-accuracy analysis uses each model's *published paid-tier
price*, recorded in `src/config.py` at freeze. In the current roster no
judge is request-per-day capped, so every judge runs the full matrix; the
pre-registered subset mechanism (first `STRONG_JUDGE_SUBSET` entries of the
committed shuffled worklist) remains in the harness for roster changes and
would be logged as a deviation if activated.

Decoding: temperature 0 for the main matrix; stability sub-study uses
temperature 0.7 × 5 resamples on a 100-item subset.

## 6. Metrics & analyses (primary in bold)

| # | Question | Metric | Unit / N | Test |
|---|---|---|---|---|
| 1a | **Judge accuracy on HARD constraints** | **accuracy vs programmatic truth + κ** | ~2,000+ constraint verdicts (all arms) | cluster bootstrap by item |
| 1b | Cross-judge holistic agreement (no truth claim) | pairwise Spearman ρ, weighted κ between judges | all items | bootstrap |
| 1c | **Sensitivity to planted violations** | **catch rate on planted cids, per judge** | ~2 planted per degraded item (~360) | binomial CI |
| 1d | Rubric value-add | 1a accuracy rubric mode vs bare-mode holistic penalty correlation | per judge | cluster bootstrap |
| 2 | **Position bias + pairwise accuracy** | flip rate A-B vs B-A; accuracy on known-dominance (mid vs degraded) pairs | ~180 pairs × 2 orders | McNemar |
| 3 | Length bias | length coefficient in regression of judge holistic on hard-pass rate + log-length | all items | cluster bootstrap CI |
| 4 | Self-preference | residual holistic (judge − hard-pass-predicted) for same-family vs other-family responses | per judge | permutation test |
| 5 | Calibration | reliability curve + ECE of confidence vs hard-constraint correctness; risk-coverage curve | all judged units | bootstrap band |
| 6 | Noise floor | per-item verdict self-agreement across 5 resamples | 100 items | descriptive |
| 7 | (optional) agreement with human mini-set | accuracy/κ vs ~100 human-labeled items | if annotated | bootstrap |

**Power (computed before data collection, `scripts/power_analysis.py`,
seed 20260813):** at item level, N=450, two judges' agreement rates must
differ by **≥7–8 pp** (base 0.7–0.8, α=0.05, power 0.8) to be detectable
(computed for the v1 sample size; the v2 worklist is ~720 units, which
only lowers this floor).
Consequence, fixed now: judge-vs-judge comparisons are **primary at the
constraint level** (~2000 units, cluster-bootstrapped by item); item-level
differences smaller than 7 pp will be reported as *not distinguishable*, and
no ranking will be claimed on them.

Multiple comparisons: Holm correction within each numbered family above.
All headline numbers carry 95% bootstrap CIs (≥2000 resamples, clustered by
item where applicable).

## 7. Budget-optimal mixed evaluation (the deliverable)

Using judged confidence (metric 5) as a triage signal, simulate policies on
held-out data: cheap-judge-only → escalate-low-confidence-to-strong-judge,
sweeping the escalation thresholds. Accuracy axis = hard-constraint truth
(the measurable slice); cost axis = published paid-tier prices. Output: cost
per 1k items vs accuracy **Pareto curve** with bootstrap bands, and 2–3
named operating points. Split: thresholds tuned on 50% of items, curve
reported on the other 50%.

## 8. Non-goals

No claim of generality beyond instruction-following in English; no
fine-tuning of judges; no more than one annotation-guide revision cycle.

## 9. Deliverables

`REPORT.md`, public gold set + annotation guide, reusable audit harness
(`src/`), one-command reproduction (`make all` given API keys).
