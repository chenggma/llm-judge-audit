#!/bin/zsh
# Daily free-tier drip: run every pipeline stage until quotas exhaust.
# Every stage is idempotent (response cache + skip logs), so this script
# is safe to run any number of times; each run makes forward progress.
# Run once a day by the launchd agent com.chesonma.judgedrip (09:00).

set -u
cd "$(dirname "$0")/.."
[ -f .env ] && source .env

# Count non-empty lines across the given files; missing files count as 0.
# Callers must pass judgment globs with zsh's (N) null-glob qualifier: an
# unmatched bare glob aborts the command substitution and leaves the variable
# empty, which then blows up the arithmetic below.
count_lines() {
  local n=0 f
  for f in "$@"; do
    [[ -f $f ]] && n=$(( n + $(grep -c . "$f" || true) ))
  done
  print -r -- $n
}

main() {
  echo "=== daily drip $(date '+%Y-%m-%d %H:%M') ==="

  local before_resp before_judg after_resp after_judg expected actual judging
  before_resp=$(count_lines data/responses/responses.jsonl)
  before_judg=$(count_lines data/judgments/*.jsonl(N))

  # 0. preconditions
  python3 scripts/validate_instructions.py || return 1

  # 1. generation (finishes in the first day or two, then no-ops)
  python3 src/generate.py

  # 2. gold sampling: only once generation is complete
  judging=yes
  if [ ! -f data/gold/worklist.jsonl ]; then
    expected=$(( $(cat data/instructions/*.jsonl | grep -c .) * 4 ))
    actual=$(grep -c . data/responses/responses.jsonl 2>/dev/null || echo 0)
    if [ "$actual" -eq "$expected" ]; then
      python3 scripts/sample_gold.py
    else
      echo "generation incomplete ($actual/$expected); judging waits"
      judging=no
    fi
  fi

  # 3. judge matrix (each mode drains what today's quotas allow)
  if [ "$judging" = "yes" ]; then
    for mode in rubric bare pairwise stability; do
      python3 src/judge.py --mode $mode
    done
  fi

  # 4. progress summary
  python3 - <<'EOF'
import json, os
for f in ("rubric", "bare", "pairwise", "stability"):
    p = f"data/judgments/{f}.jsonl"
    n = sum(1 for l in open(p)) if os.path.exists(p) else 0
    print(f"{f:10s}: {n} judgments")
EOF

  # 5. commit & push today's data increment (real work only: no-op days
  #    produce no commit). Stage data/ ONLY — `git add -A` swept whatever
  #    source edits happened to be in the tree into a commit labelled
  #    "daily drip", which misrepresents the collection history.
  if [ -n "$(git status --porcelain data)" ]; then
    git add data
    git commit -qm "daily drip $(date +%F): $(count_lines data/responses/responses.jsonl) responses, $(count_lines data/judgments/*.jsonl(N)) judgments"
    git push -q origin master || echo "push failed (offline?); will retry tomorrow"
  fi

  # 6. one-line summary the reporter quotes verbatim (grep for DRIP-SUMMARY)
  after_resp=$(count_lines data/responses/responses.jsonl)
  after_judg=$(count_lines data/judgments/*.jsonl(N))
  expected=$(( $(cat data/instructions/*.jsonl | grep -c .) * 4 ))
  echo "DRIP-SUMMARY: responses ${after_resp}/${expected} (+$((after_resp - before_resp)) today), judgments ${after_judg} (+$((after_judg - before_judg)) today)"
  echo "=== drip done ==="
}

# Self-logging. The reporter task reads data/drip.log and keys off the final
# `=== drip done ===` line, so the log must contain the tail of every run.
# This is a real pipeline, not `exec > >(tee ...)`: with process substitution
# the shell does not wait for tee, and under launchd tee was killed before it
# flushed — the DRIP-SUMMARY and done lines went missing from an exit-0 run.
# A pipeline makes the shell wait for tee; pipestatus preserves main's status.
mkdir -p data
main 2>&1 | tee -a data/drip.log
exit ${pipestatus[1]}
