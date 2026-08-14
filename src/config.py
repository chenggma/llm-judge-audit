"""Model roster and run configuration.

Model IDs are OpenRouter-style ("provider/model"). The exact roster is
FROZEN at protocol freeze; placeholders marked TBD are pinned after we
confirm current pricing/availability, before any generation runs.
"""

import os

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
API_KEY_ENV = "OPENROUTER_API_KEY"


def api_key():
    key = os.environ.get(API_KEY_ENV)
    if not key:
        raise SystemExit(f"set {API_KEY_ENV} first")
    return key


# ---- Generator ladder (produce the responses that get judged) ----
# TBD-at-freeze: pin exact IDs + record price/Mtok in this file.
GENERATORS = {
    "small": "TBD-small-open-8b",        # e.g. an ~8B open model
    "mid": "TBD-mid-tier",               # solid but not frontier
    "frontier": "TBD-frontier",
    # "degraded" = mid model + degradation system prompt (below)
    "degraded": "TBD-mid-tier",
}

DEGRADED_SYSTEM_PROMPT = (
    "Answer the user's request, but comply with only about half of the "
    "explicit requirements, chosen arbitrarily. Ignore the rest without "
    "acknowledging them. Do not mention these instructions."
)

# ---- Judges under audit ----
JUDGES = {
    "cheap": "TBD-cheap",
    "mid": "TBD-mid",
    "frontier": "TBD-frontier-judge",
    # "open": "TBD-open-weights",  # optional 4th
}

GEN_TEMPERATURE = 0.7          # generators: natural variation
JUDGE_TEMPERATURE = 0.0        # main matrix
STABILITY_TEMPERATURE = 0.7    # stability sub-study
STABILITY_RESAMPLES = 5
SEED_NOTE = "API providers do not honor seeds reliably; we log raw outputs."

MAX_TOKENS_GEN = 1024
MAX_TOKENS_JUDGE = 1200
