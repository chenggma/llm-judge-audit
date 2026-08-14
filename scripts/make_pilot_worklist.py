"""Build the 30-item PILOT annotation worklist from pilot-phase responses.

Separate file from the main worklist (which sample_gold.py builds after
full generation) so the two never collide. Stratified across arms,
shuffled, deterministic. Pilot labels calibrate the annotation guide and
do not enter the main analysis (per PROTOCOL: one guide-revision cycle
allowed after pilot).
"""

import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from generate import OUT as RESP_PATH  # noqa: E402

SEED = 20260814
N_PILOT = 30
GOLD = os.path.join(os.path.dirname(__file__), "..", "data", "gold")


def main():
    rng = random.Random(SEED)
    rows = [json.loads(l) for l in open(RESP_PATH) if l.strip()]
    by_arm = {}
    for r in rows:
        by_arm.setdefault(r["generator"], []).append(r)
    per_arm = {"small": 8, "mid": 8, "frontier": 7, "degraded": 7}
    picked = []
    for arm, k in per_arm.items():
        pool = by_arm.get(arm, [])
        rng.shuffle(pool)
        picked.extend(pool[:k])
    rng.shuffle(picked)
    os.makedirs(GOLD, exist_ok=True)
    path = os.path.join(GOLD, "pilot_worklist.jsonl")
    with open(path, "w") as f:
        for i, r in enumerate(picked[:N_PILOT]):
            f.write(json.dumps({
                "work_id": f"pilot-{i:03d}",
                "instruction_id": r["instruction_id"],
                "generator": r["generator"],
            }) + "\n")
    print(f"pilot worklist: {min(len(picked), N_PILOT)} items -> {path}")


if __name__ == "__main__":
    main()
