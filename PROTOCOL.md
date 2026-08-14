# Judge Audit — Pre-Registered Protocol

**Status: FROZEN before data collection.** This file specifies the full
experiment matrix, metrics, and decision criteria *before* any responses are
generated or judged. Results are written afterward in `REPORT.md`. Deviations,
if any, will be logged in `PROTOCOL_DEVIATIONS.md` with reasons — not silently
edited here. The git history of this file is the audit trail.

Date frozen: 2026-08-__ (filled at freeze commit)

---

## 1. Research question

LLM-as-judge is the de-facto evaluation method for instruction-following
quality, yet the judges themselves are rarely audited. We measure, for judges
across a price spectrum:

1. Agreement with human gold labels (the ceiling being human self-consistency)
2. Position bias (pairwise mode)
3. Length bias (controlling for gold quality)
4. Self-preference (judge favoring same-family outputs, controlling for gold quality)
5. Confidence calibration (does stated/derived confidence predict correctness?)
6. Stability (noise floor under resampling; sensitivity to rubric paraphrase)

and answer the engineering question: **given a budget, what mix of cheap
judge / strong judge / human review maximizes agreement with gold?**

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
  generator models (target 4: small-open ≈8B, mid-tier, frontier, and a
  deliberately degraded variant produced by prompting the mid-tier model to
  comply only partially). Ladder gives spread in true quality; degraded
  variant guarantees the low end is populated.
- **Sampling for gold**: 450 (instruction, response) pairs, stratified across
  generator models and instruction taxonomy.

## 4. Gold labels

- Unit of annotation: **per-constraint verdict** (satisfied / not satisfied /
  can't-tell) + per-item holistic score (1–5) + pairwise preference on a
  200-pair subset (same instruction, two different generators).
- Protocol: `docs/ANNOTATION_GUIDE.md` (frozen after a 30-item pilot).
- Reliability:
  - Intra-rater: 150 items re-annotated by the primary annotator ≥7 days
    later, order shuffled. Report Cohen's κ (per-constraint) and weighted κ
    (holistic).
  - Inter-rater (if budget allows): 2 external annotators × 150-item overlap
    via a crowd platform. Report pairwise κ and majority-vs-primary κ.
- **Gate**: per-constraint κ ≥ 0.60 required. If the pilot or the reliability
  check fails the gate, the annotation guide is revised and the affected
  items re-annotated; this is logged as a deviation.

## 5. Judges under audit

3–4 API judges spanning ≥10× price range (exact models fixed at freeze time
in `src/config.py`; chosen among current frontier, mid, cheap tiers, plus one
open-weights model if API access is practical), each in 2 elicitation modes:

- **Rubric mode**: judge sees instruction + response + the constraint list,
  returns per-constraint verdicts + holistic 1–5 + confidence 0–100.
- **Bare mode**: judge sees instruction + response only, returns holistic
  1–5 + confidence (no constraint list) — measures how much of judge skill
  is really rubric-following.

Pairwise mode (for position bias): rubric-style prompt, both orders (A-B,
B-A) for every pair.

Decoding: temperature 0 for the main matrix; stability sub-study uses
temperature 0.7 × 5 resamples on a 100-item subset.

## 6. Metrics & analyses (primary in bold)

| # | Question | Metric | Unit / N | Test |
|---|---|---|---|---|
| 1a | **Judge–human agreement, per-constraint** | **accuracy vs gold + Cohen's κ** | ~2000 constraint verdicts | cluster bootstrap by item |
| 1b | Judge–human agreement, holistic | Spearman ρ, quadratic-weighted κ | 450 items | bootstrap |
| 1c | Judge vs programmatic truth on HARD constraints | accuracy | ~1000 verdicts | binomial CI |
| 2 | **Position bias** | flip rate between A-B and B-A | 200 pairs × 2 orders | McNemar |
| 3 | Length bias | length coefficient in ordinal regression of judge score on gold score + log-length | 450 | cluster bootstrap CI |
| 4 | Self-preference | residual score (judge − gold-predicted) for same-family vs other-family responses | per judge | permutation test |
| 5 | Calibration | reliability curve + ECE; selective-prediction risk-coverage curve | all judged units | bootstrap band |
| 6 | Noise floor | per-item verdict self-agreement across 5 resamples | 100 items | descriptive |

**Power (computed before data collection, `scripts/power_analysis.py`,
seed 20260813):** at item level, N=450, two judges' agreement rates must
differ by **≥7–8 pp** (base 0.7–0.8, α=0.05, power 0.8) to be detectable.
Consequence, fixed now: judge-vs-judge comparisons are **primary at the
constraint level** (~2000 units, cluster-bootstrapped by item); item-level
differences smaller than 7 pp will be reported as *not distinguishable*, and
no ranking will be claimed on them.

Multiple comparisons: Holm correction within each numbered family above.
All headline numbers carry 95% bootstrap CIs (≥2000 resamples, clustered by
item where applicable).

## 7. Budget-optimal mixed evaluation (the deliverable)

Using judged confidence (metric 5) as a triage signal, simulate policies on
held-out data: cheap-judge-only → escalate-low-confidence-to-strong-judge →
escalate-to-human, sweeping the escalation thresholds. Output: cost per 1k
items vs agreement-with-gold **Pareto curve** with bootstrap bands, and 2–3
named operating points. Split: thresholds tuned on 50% of items, curve
reported on the other 50%.

## 8. Non-goals

No claim of generality beyond instruction-following in English; no
fine-tuning of judges; no more than one annotation-guide revision cycle.

## 9. Deliverables

`REPORT.md`, public gold set + annotation guide, reusable audit harness
(`src/`), one-command reproduction (`make all` given API keys).
