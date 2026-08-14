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

    if provider == "ollama":
        # native endpoint: lets us disable qwen3's thinking mode, which
        # otherwise consumes the whole token budget and returns ""
        body = {
            "model": model,
            "messages": messages,
            "think": False,
            "stream": False,
            "options": {"temperature": temperature,
                        "num_predict": max_tokens},
        }
        url = "http://localhost:11434/api/chat"
        headers = {"Content-Type": "application/json"}
    else:
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if provider == "openrouter":
            # normalized reasoning switch; without it, hybrid-reasoning
            # models (nemotron-3) emit raw CoT as content with no markers
            body["reasoning"] = {"enabled": False}
        url = config.PROVIDERS[provider]["base"] + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.provider_key(provider)}",
            "Content-Type": "application/json",
            # Cloudflare 403s the default Python-urllib UA on some providers
            "User-Agent": "judge-audit/0.1 (research; stdlib urllib)",
        }
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers=headers)
    last_err = None
    n429 = 0
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read())
            if provider == "ollama":
                content = data["message"]["content"]
                # qwen3 sometimes leaks chain-of-thought into content even
                # with think=False; keep only what follows the last
                # </think> marker
                if "</think>" in content:
                    content = content.rsplit("</think>", 1)[1]
                content = content.strip()
                usage = {"prompt_tokens": data.get("prompt_eval_count"),
                         "completion_tokens": data.get("eval_count")}
            else:
                content = data["choices"][0]["message"]["content"] or ""
                usage = data.get("usage", {})
            # reasoning models occasionally leak CoT into content on any
            # provider; strip a closed think-block, and blank the reply if
            # an unclosed one swallowed it (treated as transient below)
            if "</think>" in content:
                content = content.rsplit("</think>", 1)[1]
            elif "<think>" in content:
                content = ""
            content = content.strip()
            if not content.strip():
                # never cache an empty reply; treat as transient
                last_err = RuntimeError("empty content")
                time.sleep(2)
                continue
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
