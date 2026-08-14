"""Terminal annotation tool.

Usage:
  python scripts/annotate.py                # annotate next unlabeled items
  python scripts/annotate.py --retest      # intra-rater re-test pass
  python scripts/annotate.py --pairs       # pairwise preference pass
  python scripts/annotate.py --stats       # progress + agreement so far

Design choices that matter for label quality:
- shows constraints WITHOUT their hard/soft kind or check spec (annotator
  judges from text alone, like the judges do);
- never shows generator identity (blind);
- enforces max 40 items per sitting (drift control, per ANNOTATION_GUIDE);
- every verdict appended immediately (crash-safe), with timestamps for
  the annotation_log.
"""

import argparse
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from generate import load_instructions, OUT as RESP_PATH  # noqa: E402

GOLD = os.path.join(os.path.dirname(__file__), "..", "data", "gold")
BATCH_LIMIT = 40
RETEST_N = 150
RETEST_SEED = 20260814


def load_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def responses_by_key():
    return {(r["instruction_id"], r["generator"]): r["response"]
            for r in load_jsonl(RESP_PATH)}


def ask(prompt, valid):
    while True:
        v = input(prompt).strip().lower()
        if v in valid:
            return v
        print(f"  -> one of: {'/'.join(sorted(valid))}")


def annotate_items(retest=False, pilot=False):
    insts = {i["id"]: i for i in load_instructions()}
    resps = responses_by_key()
    wl_name = "pilot_worklist.jsonl" if pilot else "worklist.jsonl"
    worklist = load_jsonl(os.path.join(GOLD, wl_name))
    if not worklist:
        raise SystemExit(f"{wl_name} missing — run the sampling script first")
    out_name = ("labels_pilot.jsonl" if pilot
                else "labels_retest.jsonl" if retest else "labels.jsonl")
    out_path = os.path.join(GOLD, out_name)
    done = {l["work_id"] for l in load_jsonl(out_path)}

    if retest:
        primary_done = [l["work_id"] for l in
                        load_jsonl(os.path.join(GOLD, "labels.jsonl"))]
        rng = random.Random(RETEST_SEED)
        pool = list(dict.fromkeys(primary_done))
        rng.shuffle(pool)
        target = set(pool[:RETEST_N])
        todo = [w for w in worklist
                if w["work_id"] in target and w["work_id"] not in done]
    else:
        todo = [w for w in worklist if w["work_id"] not in done]

    print(f"{len(todo)} items remaining; this sitting caps at {BATCH_LIMIT}.")
    count = 0
    with open(out_path, "a") as out:
        for w in todo:
            if count >= BATCH_LIMIT:
                print("Batch limit reached — take a break (guide §hygiene).")
                break
            inst = insts[w["instruction_id"]]
            resp = resps[(w["instruction_id"], w["generator"])]
            print("\n" + "=" * 72)
            print(f"[{w['work_id']}]  ({len(done) + count + 1} labeled total)")
            print("-" * 72)
            print("INSTRUCTION:\n" + inst["prompt"])
            print("-" * 72)
            print("RESPONSE:\n" + resp)
            print("-" * 72)
            verdicts, hard_flags = {}, {}
            for c in inst["constraints"]:
                v = ask(f"  {c['cid']}: {c['text']}\n"
                        f"     [s]at / [u]nsat / [c]ant_tell: ",
                        {"s", "u", "c"})
                verdicts[c["cid"]] = {"s": "sat", "u": "unsat",
                                      "c": "cant_tell"}[v]
                hard_flags[c["cid"]] = ask(
                    "     took >30s? [y/n]: ", {"y", "n"}) == "y"
            holistic = int(ask("  holistic 1-5: ", set("12345")))
            out.write(json.dumps({
                "work_id": w["work_id"],
                "instruction_id": w["instruction_id"],
                "generator": w["generator"],
                "verdicts": verdicts, "hard": hard_flags,
                "holistic": holistic, "t": time.time(),
                "retest": retest,
            }) + "\n")
            out.flush()
            count += 1
    print(f"\nSaved {count} labels to {out_name}.")


def annotate_pairs():
    insts = {i["id"]: i for i in load_instructions()}
    resps = responses_by_key()
    pairs = load_jsonl(os.path.join(GOLD, "pairs.jsonl"))
    out_path = os.path.join(GOLD, "pair_labels.jsonl")
    done = {l["pair_id"] for l in load_jsonl(out_path)}
    todo = [p for p in pairs if p["pair_id"] not in done]
    # blind + randomize which side is shown as A
    rng = random.Random()  # true randomness fine: order is recorded
    print(f"{len(todo)} pairs remaining; cap {BATCH_LIMIT}.")
    count = 0
    with open(out_path, "a") as out:
        for p in todo:
            if count >= BATCH_LIMIT:
                break
            flip = rng.random() < 0.5
            ga, gb = (p["gen_b"], p["gen_a"]) if flip else \
                     (p["gen_a"], p["gen_b"])
            inst = insts[p["instruction_id"]]
            print("\n" + "=" * 72)
            print("INSTRUCTION:\n" + inst["prompt"])
            print("-" * 72)
            print("RESPONSE A:\n" + resps[(p["instruction_id"], ga)])
            print("-" * 72)
            print("RESPONSE B:\n" + resps[(p["instruction_id"], gb)])
            v = ask("  prefer [a] / [b] / [t]ie: ", {"a", "b", "t"})
            # map back to canonical gen_a/gen_b orientation
            if v == "t":
                pref = "tie"
            elif (v == "a") != flip:
                pref = "gen_a"
            else:
                pref = "gen_b"
            out.write(json.dumps({"pair_id": p["pair_id"], "pref": pref,
                                  "shown_flipped": flip,
                                  "t": time.time()}) + "\n")
            out.flush()
            count += 1
    print(f"\nSaved {count} pair labels.")


def stats():
    labels = load_jsonl(os.path.join(GOLD, "labels.jsonl"))
    retest = load_jsonl(os.path.join(GOLD, "labels_retest.jsonl"))
    pairs = load_jsonl(os.path.join(GOLD, "pair_labels.jsonl"))
    worklist = load_jsonl(os.path.join(GOLD, "worklist.jsonl"))
    print(f"primary labels: {len(labels)}/{len(worklist)}")
    print(f"retest labels:  {len(retest)}/{RETEST_N}")
    print(f"pair labels:    {len(pairs)}")
    if labels:
        ct = sum(v == "cant_tell" for l in labels
                 for v in l["verdicts"].values())
        tot = sum(len(l["verdicts"]) for l in labels)
        print(f"cant_tell rate: {ct}/{tot} = {ct/tot:.1%} (target <5%)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--retest", action="store_true")
    ap.add_argument("--pairs", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--pilot", action="store_true",
                    help="annotate the 30-item pilot worklist")
    a = ap.parse_args()
    if a.stats:
        stats()
    elif a.pairs:
        annotate_pairs()
    else:
        annotate_items(retest=a.retest, pilot=a.pilot)
