"""Model roster and run configuration — ZERO-BUDGET edition.

Every provider below has a free tier requiring no payment method.
The audit's cost-accuracy Pareto uses each model's PUBLISHED paid-tier
price as the cost model (recorded here at freeze), while actual calls run
on free tiers. Reported transparently in REPORT.md.

Providers (all OpenAI-compatible chat endpoints):
- google : Google AI Studio free tier (key: aistudio.google.com)
- groq   : Groq free tier             (key: console.groq.com)
- openrouter : OpenRouter free models (key: openrouter.ai, ':free' ids)
- ollama : local models via Ollama    (no key; `ollama serve`)

Free-tier daily quotas are enforced server-side; api.py treats persistent
429s as "done for today" and exits cleanly — every script is resumable.

Exact model IDs marked TBD are pinned at protocol freeze after checking
each provider's current free catalog.
"""

import os

PROVIDERS = {
    "google": {
        "base": "https://generativelanguage.googleapis.com/v1beta/openai",
        "key_env": "GEMINI_API_KEY",
    },
    "groq": {
        "base": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
    },
    "openrouter": {
        "base": "https://openrouter.ai/api/v1",
        "key_env": "OPENROUTER_API_KEY",
    },
    "ollama": {
        "base": "http://localhost:11434/v1",
        "key_env": None,  # no auth
    },
}


def provider_key(provider):
    env = PROVIDERS[provider]["key_env"]
    if env is None:
        return "ollama"
    key = os.environ.get(env)
    if not key:
        raise SystemExit(f"set {env} first (free key, see config.py header)")
    return key


# ---- Generator ladder ----
# (provider, model_id, published_price_note)
GENERATORS = {
    "small": ("ollama", "TBD-local-8b", "$0 local"),
    "mid": ("google", "TBD-flash", "TBD $/Mtok"),
    "frontier": ("google", "TBD-pro", "TBD $/Mtok"),
    "degraded": ("google", "TBD-flash", "TBD $/Mtok"),  # + system prompt
}

DEGRADED_SYSTEM_PROMPT = (
    "Answer the user's request, but comply with only about half of the "
    "explicit requirements, chosen arbitrarily. Ignore the rest without "
    "acknowledging them. Do not mention these instructions."
)

# ---- Judges under audit (cross-family on purpose: self-preference
# analysis needs judges from a different family than each generator) ----
JUDGES = {
    "cheap": ("google", "TBD-flash-lite", "TBD $/Mtok"),
    "mid-meta": ("groq", "TBD-llama-70b", "TBD $/Mtok"),
    "strong": ("google", "TBD-pro", "TBD $/Mtok"),
    "open-alt": ("openrouter", "TBD-deepseek:free", "TBD $/Mtok"),
}

# Quota-capped judges ("strong", "open-alt") run on a pre-registered
# 300-item stratified subset instead of the full 450 (subset drawn by
# scripts/sample_gold.py with the same seed; power at constraint level
# ~1300 units still clears the 7pp item-level floor comfortably).
STRONG_JUDGE_SUBSET = 300

GEN_TEMPERATURE = 0.7
JUDGE_TEMPERATURE = 0.0
STABILITY_TEMPERATURE = 0.7
STABILITY_RESAMPLES = 5
SEED_NOTE = "API providers do not honor seeds reliably; we log raw outputs."

MAX_TOKENS_GEN = 1024
MAX_TOKENS_JUDGE = 1200
