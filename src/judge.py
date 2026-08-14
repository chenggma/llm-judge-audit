"""Run the judge matrix over sampled (instruction, response) pairs.

Usage:
  python src/judge.py --mode rubric|bare          # main matrix
  python src/judge.py --mode pairwise             # position-bias study
  python src/judge.py --mode stability            # resample sub-study

Writes data/judgments/<mode>.jsonl. Idempotent via the api cache + skip log.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import api      # noqa: E402
import config   # noqa: E402
import prompts  # noqa: E402
from generate import load_instructions  # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "..", "data")


def parse_json_reply(text):
    """Judges are told 'JSON only' but models decorate; extract leniently,
    record parse failures rather than crashing (they are a finding)."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
        return None


def load_responses():
    out = []
    with open(os.path.join(DATA, "responses", "responses.jsonl")) as f:
        for line in f:
            if line.strip():
                out.append(json.loads(line))
    return out


def constraint_list_str(inst):
    return "\n".join(f"- {c['cid']}: {c['text']}" for c in inst["constraints"])


def run_single(mode, judges, temperature, resamples):
    insts = {i["id"]: i for i in load_instructions()}
    responses = load_responses()
    out_path = os.path.join(DATA, "judgments", f"{mode}.jsonl")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    done = set()
    if os.path.exists(out_path):
        with open(out_path) as f:
            for line in f:
                r = json.loads(line)
                done.add((r["instruction_id"], r["generator"],
                          r["judge"], r["call_index"]))
    tmpl = prompts.RUBRIC_JUDGE if mode in ("rubric", "stability") \
        else prompts.BARE_JUDGE
    with open(out_path, "a") as out:
        for resp in responses:
            inst = insts[resp["instruction_id"]]
            for judge_name, judge_model in judges.items():
                for k in range(resamples):
                    key = (inst["id"], resp["generator"], judge_name, k)
                    if key in done:
                        continue
                    prompt = tmpl.format(
                        instruction=inst["prompt"],
                        response=resp["response"],
                        constraint_list=constraint_list_str(inst))
                    raw = api.chat(judge_model,
                                   [{"role": "user", "content": prompt}],
                                   temperature, config.MAX_TOKENS_JUDGE,
                                   call_index=k)
                    parsed = parse_json_reply(raw)
                    out.write(json.dumps({
                        "instruction_id": inst["id"],
                        "generator": resp["generator"],
                        "judge": judge_name, "mode": mode, "call_index": k,
                        "parsed": parsed, "parse_ok": parsed is not None,
                        "raw": raw if parsed is None else None,
                    }) + "\n")
                    out.flush()
                    print(f"{inst['id']} {resp['generator']} {judge_name} #{k}"
                          f" parse_ok={parsed is not None}")


def run_pairwise(judges):
    """A-B and B-A for every sampled pair (pairs file built by
    scripts/sample_pairs.py)."""
    insts = {i["id"]: i for i in load_instructions()}
    pairs_path = os.path.join(DATA, "gold", "pairs.jsonl")
    if not os.path.exists(pairs_path):
        raise SystemExit("run scripts/sample_pairs.py first")
    responses = {(r["instruction_id"], r["generator"]): r["response"]
                 for r in load_responses()}
    out_path = os.path.join(DATA, "judgments", "pairwise.jsonl")
    done = set()
    if os.path.exists(out_path):
        with open(out_path) as f:
            for line in f:
                r = json.loads(line)
                done.add((r["pair_id"], r["judge"], r["order"]))
    with open(pairs_path) as f, open(out_path, "a") as out:
        for line in f:
            pair = json.loads(line)
            inst = insts[pair["instruction_id"]]
            ra = responses[(pair["instruction_id"], pair["gen_a"])]
            rb = responses[(pair["instruction_id"], pair["gen_b"])]
            for judge_name, judge_model in judges.items():
                for order, (x, y) in (("AB", (ra, rb)), ("BA", (rb, ra))):
                    if (pair["pair_id"], judge_name, order) in done:
                        continue
                    prompt = prompts.PAIRWISE_JUDGE.format(
                        instruction=inst["prompt"],
                        response_a=x, response_b=y)
                    raw = api.chat(judge_model,
                                   [{"role": "user", "content": prompt}],
                                   config.JUDGE_TEMPERATURE,
                                   config.MAX_TOKENS_JUDGE)
                    parsed = parse_json_reply(raw)
                    out.write(json.dumps({
                        "pair_id": pair["pair_id"], "judge": judge_name,
                        "order": order, "parsed": parsed,
                        "parse_ok": parsed is not None,
                        "raw": raw if parsed is None else None,
                    }) + "\n")
                    out.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True,
                    choices=["rubric", "bare", "pairwise", "stability"])
    args = ap.parse_args()
    if args.mode == "pairwise":
        run_pairwise(config.JUDGES)
    elif args.mode == "stability":
        run_single("stability", config.JUDGES,
                   config.STABILITY_TEMPERATURE, config.STABILITY_RESAMPLES)
    else:
        run_single(args.mode, config.JUDGES, config.JUDGE_TEMPERATURE, 1)


if __name__ == "__main__":
    main()
