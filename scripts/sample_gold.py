"""Build the gold annotation sample: stratified across generator ladder and
instruction domain, shuffled with a fixed seed, written as an ordered
worklist for the annotation tool. Also samples the pairwise subset.

Run ONCE after generation completes; committed output makes the sample
auditable. Deterministic (seed in PROTOCOL).
"""

import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from generate import load_instructions, OUT as RESP_PATH  # noqa: E402

SEED = 20260813
N_GOLD = 450
N_PAIRS = 200
GOLD_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "gold")


def main():
    rng = random.Random(SEED)
    insts = {i["id"]: i for i in load_instructions()}
    responses = []
    with open(RESP_PATH) as f:
        for line in f:
            if line.strip():
                responses.append(json.loads(line))

    # Stratify: proportional across (generator, domain) cells.
    cells = {}
    for r in responses:
        key = (r["generator"], insts[r["instruction_id"]]["domain"])
        cells.setdefault(key, []).append(r)
    total = len(responses)
    picked = []
    for key, items in sorted(cells.items()):
        k = round(N_GOLD * len(items) / total)
        rng.shuffle(items)
        picked.extend(items[:k])
    rng.shuffle(picked)
    picked = picked[:N_GOLD]

    os.makedirs(GOLD_DIR, exist_ok=True)
    with open(os.path.join(GOLD_DIR, "worklist.jsonl"), "w") as f:
        for i, r in enumerate(picked):
            f.write(json.dumps({
                "work_id": f"w{i:04d}",
                "instruction_id": r["instruction_id"],
                "generator": r["generator"],
            }) + "\n")

    # Pairwise subset: same instruction, two different generators, both in
    # the gold sample where possible.
    by_inst = {}
    for r in picked:
        by_inst.setdefault(r["instruction_id"], []).append(r["generator"])
    candidates = [(iid, gens) for iid, gens in by_inst.items()
                  if len(set(gens)) >= 2]
    rng.shuffle(candidates)
    pairs = []
    for iid, gens in candidates:
        gens = sorted(set(gens))
        a, b = rng.sample(gens, 2)
        pairs.append({"pair_id": f"p{len(pairs):04d}",
                      "instruction_id": iid, "gen_a": a, "gen_b": b})
        if len(pairs) >= N_PAIRS:
            break
    with open(os.path.join(GOLD_DIR, "pairs.jsonl"), "w") as f:
        for p in pairs:
            f.write(json.dumps(p) + "\n")

    print(f"gold worklist: {len(picked)} items; pairs: {len(pairs)}")


if __name__ == "__main__":
    main()
