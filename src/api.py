"""Minimal multi-provider chat client (OpenAI-compatible endpoints).
Pure stdlib (urllib), with retries, on-disk response cache, a cost ledger,
and free-tier quota awareness.

Every call is cached by a hash of (provider, model, messages, temperature,
max_tokens, call_index) so re-running never re-spends quota; the cache
directory is the raw-data artifact committed to the repo.

Free-tier behavior: persistent 429s raise QuotaExhausted; batch scripts
catch it, exit cleanly, and tomorrow's run resumes from cache.
"""

import hashlib
import json
import os
import time
import urllib.error
import urllib.request

import config

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cache")
LEDGER = os.path.join(CACHE_DIR, "call_ledger.jsonl")


class QuotaExhausted(Exception):
    """Provider free-tier quota hit; resume tomorrow."""


def _cache_path(payload_key):
    h = hashlib.sha256(payload_key.encode()).hexdigest()[:24]
    return os.path.join(CACHE_DIR, f"{h}.json")


def chat(provider, model, messages, temperature, max_tokens,
         call_index=0, system=None):
    """One chat completion. call_index distinguishes deliberate resamples
    of an otherwise-identical call (stability sub-study)."""
    if system:
        messages = [{"role": "system", "content": system}] + messages
    key = json.dumps([provider, model, messages, temperature, max_tokens,
                      call_index], sort_keys=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = _cache_path(key)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)["content"]

    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        config.PROVIDERS[provider]["base"] + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {config.provider_key(provider)}",
            "Content-Type": "application/json",
        },
    )
    last_err = None
    n429 = 0
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read())
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            with open(path, "w") as f:
                json.dump({"content": content, "usage": usage,
                           "provider": provider, "model": model,
                           "call_index": call_index}, f)
            with open(LEDGER, "a") as f:
                f.write(json.dumps({"t": time.time(), "provider": provider,
                                    "model": model, "usage": usage}) + "\n")
            return content
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429:
                n429 += 1
                if n429 >= 3:
                    # RPM backoff exhausted -> almost certainly daily quota
                    raise QuotaExhausted(f"{provider}/{model}")
                time.sleep(30 * n429)
                continue
            if e.code in (500, 502, 503):
                time.sleep(2 ** attempt * 2)
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
            time.sleep(2 ** attempt * 2)
    raise RuntimeError(f"gave up on {provider}/{model}: {last_err}")
