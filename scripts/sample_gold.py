"""Build the judging worklist and pairwise set (design v2, no human gold).

- worklist.jsonl: ALL (instruction, response) units in a committed,
  seeded shuffle. Judging covers everything; the shuffle order defines the
  pre-registered subsets (first STRONG_JUDGE_SUBSET for any quota-capped
  judge, first STABILITY_SUBSET for the resample sub-study).
- pairs.jsonl: known-dominance pairs — (mid, degraded-of-that-same-mid)
  per instruction. The degraded member is the same mid response with
  verified planted violations, so the correct preference is known by
  construction. Used for pairwise accuracy AND position bias.

Run ONCE after generation completes; committed output makes the sample
auditable. Deterministic.
"""

import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from generate import load_instructions, OUT as RESP_PATH  # noqa: E402

SEED = 20260813
GOLD_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "gold")


def main():
    rng = random.Random(SEED)
    insts = {i["id"]: i for i in load_instructions()}
    responses = []
    with open(RESP_PATH) as f:
        for line in f:
            if line.strip():
                responses.append(json.loads(line))

    picked = list(responses)
    rng.shuffle(picked)

    os.makedirs(GOLD_DIR, exist_ok=True)
    with open(os.path.join(GOLD_DIR, "worklist.jsonl"), "w") as f:
        for i, r in enumerate(picked):
            f.write(json.dumps({
                "work_id": f"w{i:04d}",
                "instruction_id": r["instruction_id"],
                "generator": r["generator"],
            }) + "\n")

    # Known-dominance pairs: mid vs degraded(mid), same instruction.
    have = {(r["instruction_id"], r["generator"]) for r in responses}
    planted = {r["instruction_id"]: r.get("planted_cids", [])
               for r in responses if r["generator"] == "degraded"}
    pairs = []
    for iid in sorted(insts):
        if (iid, "mid") in have and (iid, "degraded") in have \
                and planted.get(iid):
            pairs.append({
                "pair_id": f"p{len(pairs):04d}",
                "instruction_id": iid,
                "gen_a": "mid", "gen_b": "degraded",
                "known_better": "gen_a",
                "planted_cids": planted[iid],
            })
    with open(os.path.join(GOLD_DIR, "pairs.jsonl"), "w") as f:
        for p in pairs:
            f.write(json.dumps(p) + "\n")

    print(f"worklist: {len(picked)} units; known-dominance pairs: {len(pairs)}")


if __name__ == "__main__":
    main()
