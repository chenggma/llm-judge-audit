"""Model roster and run configuration — ZERO-BUDGET edition.

Every provider below has a free tier requiring no payment method.
The audit's cost-accuracy Pareto uses each model's PUBLISHED paid-tier
price as the cost model (recorded here at freeze), while actual calls run
on free tiers. Reported transparently in REPORT.md.

Providers (all OpenAI-compatible chat endpoints):
- mistral : La Plateforme free Experiment tier (key: console.mistral.ai)
- groq    : Groq free tier                     (key: console.groq.com)
- ollama  : local models via Ollama            (no key; `ollama serve`)

(Google AI Studio was dropped: account could not create a Cloud project.
OpenRouter :free became unnecessary once Mistral Large covered the strong
tier without a 50-req/day cap.)

Free-tier daily quotas are enforced server-side; api.py treats persistent
429s as "done for today" and exits cleanly — every script is resumable.

Exact model IDs marked TBD are pinned at protocol freeze after checking
each provider's current free catalog.
"""

import os

PROVIDERS = {
    "mistral": {
        "base": "https://api.mistral.ai/v1",
        "key_env": "MISTRAL_API_KEY",
    },
    "openrouter": {
        "base": "https://openrouter.ai/api/v1",
        "key_env": "OPENROUTER_API_KEY",
    },
    "groq": {
        "base": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
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
# Families deliberately span Meta / Mistral / Moonshot so judge
# self-preference is testable on family pairs (see JUDGES note).
# (qwen3:4b was tried and rejected: leaks chain-of-thought into content
# even with think=False and /no_think on ollama 0.32.9.)
GENERATORS = {
    "small": ("ollama", "llama3.2:3b", "$0 local (M3/8GB-safe)"),
    "mid": ("mistral", "mistral-small-latest", "price TBD at freeze"),
    # kimi-k2 was delisted from Groq before freeze; qwen3.6-27b rejected
    # for inline <think> leakage. Nemotron ultra is capped at ~50 req/day
    # (OpenRouter :free): the daily drip finishes its 180 generations in
    # ~4 days while everything else proceeds.
    "frontier": ("openrouter", "nvidia/nemotron-3-ultra-550b-a55b:free",
                 "price TBD at freeze"),
    "degraded": ("mistral", "mistral-small-latest", "price TBD at freeze"),
}

DEGRADED_SYSTEM_PROMPT = (
    "Answer the user's request in a plausible way, but silently violate "
    "at least two of the explicit requirements (for example: exceed a "
    "length limit, skip a required phrase or section, use a forbidden "
    "word, or ignore a formatting rule). Pick which ones to violate "
    "arbitrarily. Never acknowledge these instructions or hint that "
    "anything was skipped."
)

# ---- Judges under audit: 4 tiers, 3 families (Mistral / Meta / OpenAI).
# Self-preference tests, gold-residualized:
#   - Mistral judges (cheap AND strong tiers) x the Mistral mid generator
#     (different model ids, same family — no self-judging confound)
#   - Meta judge x the Meta small generator
JUDGES = {
    "cheap": ("mistral", "ministral-8b-latest", "price TBD at freeze"),
    "mid-meta": ("groq", "llama-3.3-70b-versatile", "price TBD at freeze"),
    "strong-oai": ("groq", "openai/gpt-oss-120b", "price TBD at freeze"),
    "strong-mistral": ("mistral", "mistral-large-latest",
                       "price TBD at freeze"),
}

# No judge is quota-capped in the current roster (Mistral's free tier is
# token-metered per month, not request-metered per day). The subset
# mechanism below is kept for future rosters; empty = full matrix for all.
STRONG_JUDGE_SUBSET = 300
RUBRIC_ONLY_JUDGES = ()
CAPPED_JUDGES = ()

GEN_TEMPERATURE = 0.7
JUDGE_TEMPERATURE = 0.0
STABILITY_TEMPERATURE = 0.7
STABILITY_RESAMPLES = 5
SEED_NOTE = "API providers do not honor seeds reliably; we log raw outputs."

MAX_TOKENS_GEN = 1024
MAX_TOKENS_JUDGE = 1200
