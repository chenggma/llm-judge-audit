"""Generate responses from the generator ladder for every instruction.

Usage: python src/generate.py [--limit N]
Writes data/responses/responses.jsonl (append-safe via cache; idempotent).
"""

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import api      # noqa: E402
import degrade  # noqa: E402
import config   # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "responses",
                   "responses.jsonl")


def load_instructions():
    insts = []
    for path in sorted(glob.glob(os.path.join(
            os.path.dirname(__file__), "..", "data", "instructions",
            "*.jsonl"))):
        with open(path) as f:
            for line in f:
                if line.strip():
                    insts.append(json.loads(line))
    return insts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="only first N instructions (pilot)")
    args = ap.parse_args()

    insts = load_instructions()
    if args.limit:
        insts = insts[:args.limit]

    done = set()
    if os.path.exists(OUT):
        with open(OUT) as f:
            for line in f:
                r = json.loads(line)
                done.add((r["instruction_id"], r["generator"]))

    mid_texts = {}
    if os.path.exists(OUT):
        with open(OUT) as f:
            for line in f:
                r = json.loads(line)
                if r["generator"] == "mid":
                    mid_texts[r["instruction_id"]] = r["response"]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    exhausted = set()
    with open(OUT, "a") as out:
        for inst in insts:
            for gen_name, (provider, model, _price) in \
                    config.GENERATORS.items():
                if (inst["id"], gen_name) in done:
                    continue
                extra = {}
                if gen_name == "degraded":
                    # constructed-violation arm: no API call (src/degrade.py)
                    if inst["id"] not in mid_texts:
                        continue  # mid not generated yet; next run
                    text, planted = degrade.degrade(
                        inst, mid_texts[inst["id"]])
                    extra = {"planted_cids": planted}
                else:
                    if provider in exhausted:
                        continue
                    try:
                        text = api.chat(
                            provider, model,
                            [{"role": "user", "content": inst["prompt"]}],
                            config.GEN_TEMPERATURE, config.MAX_TOKENS_GEN)
                    except api.QuotaExhausted as e:
                        print(f"quota done for today on {provider} ({e}); "
                              "other providers continue")
                        exhausted.add(provider)
                        continue
                    if gen_name == "mid":
                        mid_texts[inst["id"]] = text
                out.write(json.dumps({
                    "instruction_id": inst["id"],
                    "generator": gen_name,
                    "model": model if gen_name != "degraded"
                    else "degrade.py(mid)",
                    "response": text, **extra,
                }) + "\n")
                out.flush()
                print(f"{inst['id']} x {gen_name}: {len(text)} chars")


if __name__ == "__main__":
    main()
