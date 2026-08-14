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

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "a") as out:
        for inst in insts:
            for gen_name, model in config.GENERATORS.items():
                if (inst["id"], gen_name) in done:
                    continue
                system = (config.DEGRADED_SYSTEM_PROMPT
                          if gen_name == "degraded" else None)
                text = api.chat(
                    model,
                    [{"role": "user", "content": inst["prompt"]}],
                    config.GEN_TEMPERATURE, config.MAX_TOKENS_GEN,
                    system=system)
                out.write(json.dumps({
                    "instruction_id": inst["id"],
                    "generator": gen_name,
                    "model": model,
                    "response": text,
                }) + "\n")
                out.flush()
                print(f"{inst['id']} x {gen_name}: {len(text)} chars")


if __name__ == "__main__":
    main()
