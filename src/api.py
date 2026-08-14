"""Minimal OpenRouter chat client. Pure stdlib (urllib), with retries,
on-disk response cache, and a cost ledger.

Every call is cached by a hash of (model, messages, temperature, max_tokens,
call_index) so re-running a script never re-spends; the cache directory is
the raw-data artifact committed to the repo (responses are data here, not
transient).
"""

import hashlib
import json
import os
import time
import urllib.error
import urllib.request

import config

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cache")
LEDGER = os.path.join(CACHE_DIR, "cost_ledger.jsonl")


def _cache_path(payload_key):
    h = hashlib.sha256(payload_key.encode()).hexdigest()[:24]
    return os.path.join(CACHE_DIR, f"{h}.json")


def chat(model, messages, temperature, max_tokens, call_index=0, system=None):
    """One chat completion. call_index distinguishes deliberate resamples
    of an otherwise-identical call (stability sub-study)."""
    if system:
        messages = [{"role": "system", "content": system}] + messages
    key = json.dumps([model, messages, temperature, max_tokens, call_index],
                     sort_keys=True)
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
        config.OPENROUTER_BASE + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {config.api_key()}",
            "Content-Type": "application/json",
        },
    )
    last_err = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            with open(path, "w") as f:
                json.dump({"content": content, "usage": usage,
                           "model": model, "call_index": call_index}, f)
            with open(LEDGER, "a") as f:
                f.write(json.dumps({"t": time.time(), "model": model,
                                    "usage": usage}) + "\n")
            return content
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 500, 502, 503):
                time.sleep(2 ** attempt * 2)
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
            time.sleep(2 ** attempt * 2)
    raise RuntimeError(f"gave up on {model}: {last_err}")
