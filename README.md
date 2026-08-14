# llm-judge-audit

How trustworthy is LLM-as-judge? A pre-registered audit of judge models on
instruction-following evaluation — agreement with human gold labels,
position/length/self-preference biases, confidence calibration, noise floor —
ending in a budget-optimal mixed evaluation policy (cheap judge → strong
judge → human) with a cost-accuracy Pareto curve.

**Status: protocol phase.** [PROTOCOL.md](PROTOCOL.md) is frozen before any
data collection; results land in `REPORT.md` when the matrix completes.
The minimal detectable effect was computed *before* data collection
(`scripts/power_analysis.py`): at N=450 items, judge-vs-judge agreement
differences under ~7 pp are not resolvable at the item level and will not be
ranked — constraint-level analysis (~2,000 units) is primary.

## Layout

- `PROTOCOL.md` — pre-registered design, metrics, decision rules
- `docs/ANNOTATION_GUIDE.md` — human labeling protocol (κ-gated)
- `data/instructions/` — authored multi-constraint instruction set
- `src/` — generation, judging, hard-constraint verification
- `scripts/` — power analysis, sampling, annotation tool, validation
- `analysis/` — metrics + figures (added with results)

## Reproduce

```
# free-tier keys (no payment method needed):
export GEMINI_API_KEY=...       # aistudio.google.com
export GROQ_API_KEY=...         # console.groq.com
export OPENROUTER_API_KEY=...   # openrouter.ai (':free' models)
# plus a local model: ollama serve
python scripts/validate_instructions.py
python src/generate.py
python scripts/sample_gold.py
# human annotation: python scripts/annotate.py (see ANNOTATION_GUIDE)
python src/judge.py --mode rubric && python src/judge.py --mode bare
python src/judge.py --mode pairwise && python src/judge.py --mode stability
# analysis notebooks/scripts: analysis/
```

All API responses are cached under `data/cache/` and committed: the raw data
of record. Total API spend is logged in `data/cache/cost_ledger.jsonl`.
