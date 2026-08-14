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
# Families deliberately span Meta / Google / Moonshot so judge
# self-preference is testable on two family pairs: Google judges x the
# Google generator, and the Meta judge x the Meta generator.
# (qwen3:4b was tried and rejected: leaks chain-of-thought into content
# even with think=False and /no_think on ollama 0.32.9.)
GENERATORS = {
    "small": ("ollama", "llama3.2:3b", "$0 local (M3/8GB-safe)"),
    "mid": ("google", "gemini-3.5-flash", "price TBD at freeze"),
    "frontier": ("groq", "moonshotai/kimi-k2-instruct",
                 "price TBD at freeze"),
    "degraded": ("google", "gemini-3.5-flash", "price TBD at freeze"),
}

DEGRADED_SYSTEM_PROMPT = (
    "Answer the user's request, but comply with only about half of the "
    "explicit requirements, chosen arbitrarily. Ignore the rest without "
    "acknowledging them. Do not mention these instructions."
)

# ---- Judges under audit: 4 tiers, 3 families (Google / Meta / OpenAI /
# NVIDIA). Self-preference primary test: Google judges on the Google
# generator's outputs vs others, gold-residualized. ----
JUDGES = {
    "cheap": ("google", "gemini-3.5-flash-lite", "price TBD at freeze"),
    "mid-meta": ("groq", "llama-3.3-70b-versatile", "price TBD at freeze"),
    "strong-oai": ("groq", "openai/gpt-oss-120b", "price TBD at freeze"),
    "ultra": ("openrouter", "nvidia/nemotron-3-ultra-550b-a55b:free",
              "price TBD at freeze"),
}

# The OpenRouter free tier allows ~50 requests/day: "ultra" runs RUBRIC
# MODE ONLY on a pre-registered stratified subset (the first
# STRONG_JUDGE_SUBSET entries of the committed shuffled worklist),
# ~6 quota-days. All other judges run the full matrix.
STRONG_JUDGE_SUBSET = 300
RUBRIC_ONLY_JUDGES = ("ultra",)
CAPPED_JUDGES = ("ultra",)

GEN_TEMPERATURE = 0.7
JUDGE_TEMPERATURE = 0.0
STABILITY_TEMPERATURE = 0.7
STABILITY_RESAMPLES = 5
SEED_NOTE = "API providers do not honor seeds reliably; we log raw outputs."

MAX_TOKENS_GEN = 1024
MAX_TOKENS_JUDGE = 1200
