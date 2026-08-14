# Annotation Guide — v0.1 (pilot draft)

**Status: DRAFT until the 30-item pilot; frozen afterward.** Version bumps
after freeze are protocol deviations and get logged.

You are labeling whether a model response satisfies each explicit constraint
of an instruction, plus an overall quality score. Judge **only what is on the
page** — never what the model "probably meant."

## Per-constraint verdict (the primary label)

For each listed constraint, exactly one of:

| Verdict | Meaning |
|---|---|
| `sat` | The response satisfies the constraint, fully. |
| `unsat` | It does not, or only partially. **Partial = unsat.** |
| `cant_tell` | You cannot decide from the text alone (use sparingly; target <5%). |

### Rules

1. **Partial compliance is `unsat`.** "List 5 reasons" answered with 4 good
   reasons → `unsat`. The holistic score is where partial credit lives, not
   the verdict.
2. **Letter over spirit for HARD constraints.** "Under 100 words" with 103
   words → `unsat`, even if trimming would be trivial.
3. **Spirit over letter for SOFT constraints.** "Explain like I'm five"
   satisfied by any genuinely lay-accessible explanation — it does not need
   to literally address a child.
4. **Constraints are independent.** A response that ignores the topic but
   nails the format gets `sat` on format constraints. Do not let global
   quality bleed into individual verdicts (halo effect — the main annotator
   failure mode this guide exists to prevent).
5. **`cant_tell` is for epistemic limits, not difficulty.** Use it when the
   constraint references something you cannot verify (e.g. "use only
   ingredients available in a typical US supermarket" and you genuinely don't
   know one item). If you're just torn, decide, and flag with `hard: true`.
6. **No outside tools.** No searching, no running code. If a factual-accuracy
   constraint can't be settled from general knowledge → `cant_tell`.
7. Mark `hard: true` on any verdict that took you >30s of deliberation.
   (These items get analyzed separately as the "human-hard" stratum.)

## Holistic score (1–5)

Score the response as an answer to the instruction, all things considered:

| Score | Anchor |
|---|---|
| 5 | Satisfies every constraint; content is accurate and genuinely useful. Nothing to fix. |
| 4 | At most one minor constraint miss OR minor content weakness; a user would still be happy. |
| 3 | Useful core, but a notable miss: a clearly failed constraint, or mediocre content despite compliance. |
| 2 | Multiple failed constraints or substantially wrong/thin content; user would need to re-prompt. |
| 1 | Ignores the instruction, off-topic, refuses without cause, or incoherent. |

Score content quality *and* compliance; the anchors above set the exchange
rate. Do not average constraint verdicts mechanically — a response can be
`sat` on 5/5 constraints and still be a 3 (technically compliant, hollow).

## Pairwise preference (subset)

Given the same instruction and two responses A/B: pick `A`, `B`, or `tie`.
Decision rule, in order: (1) which satisfies more constraints; (2) if equal,
which has better content; (3) if still genuinely equal, `tie`. Target tie
rate <20%. You will see pairs in randomized order and blind to which model
produced which response.

## Session hygiene (drift control)

- Batches of ≤40 items; break between batches. Max ~80 items/day.
- Never annotate two responses to the same instruction back-to-back within
  a batch (the tool enforces shuffling).
- Re-read this guide at the start of each day, before the first batch.
- If you notice your standard drifting mid-session (e.g. you'd now grade an
  earlier item differently), stop the batch and note it in
  `data/gold/annotation_log.md`.

## Worked examples

(3 worked items with filled labels to be added from the pilot before freeze —
one clean `sat`-heavy case, one partial-compliance case, one `cant_tell`
case.)
