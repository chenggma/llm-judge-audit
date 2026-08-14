"""Constructed-violation arm: mechanically plant hard-constraint violations
into the mid generator's response.

Why mechanical: aligned API models refuse to be sloppy on purpose (two
prompt-based attempts documented in git history produced 0 violations).
Planting violations programmatically is also better measurement: each
degraded response carries *known-by-construction* unsat labels on the
planted constraints, giving an exact per-item test of judge sensitivity
(did the judge catch the planted banned word?).

Deterministic per instruction (seeded by instruction id). At least two
hard constraints are violated per item. Planted violations are recorded
alongside the response for analysis.
"""

import json
import random

FILLER = [
    "On a related note, it is worth adding a few additional thoughts here "
    "for completeness, even if they slightly repeat earlier points.",
    "To elaborate further, there are several tangential considerations "
    "that could also be mentioned in this context, broadly speaking.",
    "As an aside, many people find that circumstances like these vary "
    "considerably from case to case, all things considered.",
    "It should additionally be noted that this topic connects to several "
    "broader themes worth keeping in mind going forward.",
]


def _violate(check, text, rng):
    """Return transformed text violating one hard check, or None if this
    check type can't be reliably violated for this text."""
    ctype, val = check["type"], check["value"]

    if ctype == "word_count_max":
        extra = []
        need = val - len(text.split()) + 25
        while sum(len(f.split()) for f in extra) < max(need, 30):
            extra.append(rng.choice(FILLER))
        return text + "\n\n" + " ".join(extra)
    if ctype == "word_count_min":
        words = text.split()
        keep = max(5, int(val * 0.6))
        return " ".join(words[:keep])
    if ctype == "contains":
        low = text.lower()
        idx = low.find(val.lower())
        if idx < 0:
            return None
        return text[:idx] + text[idx + len(val):]
    if ctype == "not_contains":
        sents = text.split(". ")
        pos = rng.randrange(len(sents))
        sents[pos] = sents[pos] + f" — {val}, so to speak"
        return ". ".join(sents)
    if ctype == "ends_with":
        return (text + "\n\nP.S. Let me know if you need anything else "
                "at all, any time.")
    if ctype == "starts_with":
        return "Sure! Here is what you asked for.\n\n" + text
    if ctype in ("paragraph_count", "bullet_count", "numbered_items"):
        return text + "\n\n" + rng.choice(FILLER)
    if ctype == "section_headers":
        target = val[-1]
        if target not in text:
            return None
        return text.replace(target, target + " and other thoughts", 1)
    if ctype == "sentence_count_max":
        return (text + " " + rng.choice(FILLER) + " " + rng.choice(FILLER))
    if ctype == "json_valid":
        return "Here is the JSON you requested:\n\n" + text + "\n\nHope this helps!"
    if ctype == "question_count":
        return text + " Also, does that all make sense?"
    return None


def degrade(instruction, mid_response, min_violations=2):
    """Plant >= min_violations hard-constraint violations into
    mid_response. Returns (degraded_text, planted_cids). Deterministic
    per instruction id.

    Every plant is verified with verify_hard before being recorded: a
    transform that leaves the check passing (or that a later transform
    accidentally re-satisfies) is not counted. 'planted_cids' therefore
    means verified-failing, by construction."""
    import verify_hard
    rng = random.Random(f"degrade-{instruction['id']}")
    hard = {c["cid"]: c for c in instruction["constraints"]
            if c["kind"] == "hard"}
    order = list(hard)
    rng.shuffle(order)
    text = mid_response
    attempted = []
    for cid in order:
        if len(attempted) >= min_violations and rng.random() < 0.5:
            continue  # sometimes plant more than 2, usually stop
        new = _violate(hard[cid]["check"], text, rng)
        if new is not None and not verify_hard.check(new, hard[cid]["check"]):
            text = new
            attempted.append(cid)
    # final verification pass: a later transform can re-break or re-satisfy
    # an earlier one; report only what actually fails in the final text
    planted = [cid for cid in attempted
               if not verify_hard.check(text, hard[cid]["check"])]
    return text, planted


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "src")
    import verify_hard
    insts = [json.loads(l) for l in
             open("data/instructions/seed_batch_01.jsonl") if l.strip()][:3]
    resp = {json.loads(l)["instruction_id"]: json.loads(l)["response"]
            for l in open("data/responses/responses.jsonl")
            if json.loads(l)["generator"] == "mid"}
    for inst in insts:
        if inst["id"] not in resp:
            continue
        text, planted = degrade(inst, resp[inst["id"]])
        checks = verify_hard.verify_response(inst, text)
        print(inst["id"], "planted:", planted,
              "verified-failing:", [c for c, ok in checks.items() if not ok])
