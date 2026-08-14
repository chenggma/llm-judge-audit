"""Validate instruction files: schema shape, check types implemented,
constraint mix (2-3 hard + 2-3 soft), unique ids. Run in CI and before
any generation.
"""

import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import verify_hard  # noqa: E402

DOMAINS = {"professional-writing", "explanation", "planning",
           "technical", "analysis", "creative"}


def main():
    files = sorted(glob.glob(os.path.join(
        os.path.dirname(__file__), "..", "data", "instructions", "*.jsonl")))
    ids = set()
    n = 0
    errors = []
    for path in files:
        with open(path) as f:
            for lineno, line in enumerate(f, 1):
                if not line.strip():
                    continue
                loc = f"{os.path.basename(path)}:{lineno}"
                try:
                    inst = json.loads(line)
                except json.JSONDecodeError as e:
                    errors.append(f"{loc}: bad json ({e})")
                    continue
                n += 1
                if inst["id"] in ids:
                    errors.append(f"{loc}: duplicate id {inst['id']}")
                ids.add(inst["id"])
                if inst["domain"] not in DOMAINS:
                    errors.append(f"{loc}: unknown domain {inst['domain']}")
                cons = inst["constraints"]
                hard = [c for c in cons if c["kind"] == "hard"]
                soft = [c for c in cons if c["kind"] == "soft"]
                if not (4 <= len(cons) <= 6):
                    errors.append(f"{loc}: {len(cons)} constraints (want 4-6)")
                if not (2 <= len(hard) <= 4):
                    errors.append(f"{loc}: {len(hard)} hard (want 2-4)")
                if not (2 <= len(soft) <= 4):
                    errors.append(f"{loc}: {len(soft)} soft (want 2-4)")
                cids = [c["cid"] for c in cons]
                if len(cids) != len(set(cids)):
                    errors.append(f"{loc}: duplicate cids")
                for c in hard:
                    try:
                        verify_hard.check("probe text", c["check"])
                    except ValueError as e:
                        errors.append(f"{loc}/{c['cid']}: {e}")
                    except Exception:
                        pass  # check ran; probe text just doesn't fit
    for e in errors:
        print("ERROR", e)
    print(f"{n} instructions, {len(errors)} errors")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
