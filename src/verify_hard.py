"""Mechanical verification of HARD constraints.

These verdicts are programmatic ground truth: they anchor both human and
judge error rates on the verifiable slice of the task. Pure stdlib.
"""

import json
import re

BULLET_RE = re.compile(r"^\s*[-*•]\s+")
NUMBERED_RE = re.compile(r"^\s*(\d+)[.)]\s+")


def _words(text):
    return text.split()


def _paragraphs(text):
    return [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]


def _sentences(text):
    # naive but deterministic; documented limitation
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s for s in parts if s.strip()]


def check(response, check_spec):
    """Return True/False for one hard-constraint check on a response."""
    ctype = check_spec["type"]
    val = check_spec["value"]
    text = response.strip()

    if ctype == "word_count_max":
        return len(_words(text)) <= val
    if ctype == "word_count_min":
        return len(_words(text)) >= val
    if ctype == "bullet_count":
        return sum(1 for ln in text.splitlines() if BULLET_RE.match(ln)) == val
    if ctype == "numbered_items":
        nums = [int(m.group(1)) for ln in text.splitlines()
                if (m := NUMBERED_RE.match(ln))]
        return nums == list(range(1, val + 1))
    if ctype == "paragraph_count":
        return len(_paragraphs(text)) == val
    if ctype == "contains":
        return val.lower() in text.lower()
    if ctype == "not_contains":
        needle = val.lower()
        if len(needle) == 1 or not needle.isalnum():
            return needle not in text.lower()
        return re.search(rf"\b{re.escape(needle)}\b", text.lower()) is None
    if ctype == "section_headers":
        pos = -1
        low = text.lower()
        for header in val:
            idx = low.find(header.lower())
            if idx <= pos:
                return False
            pos = idx
        return True
    if ctype == "starts_with":
        return text.startswith(val)
    if ctype == "ends_with":
        return text.rstrip().endswith(val)
    if ctype == "sentence_count_max":
        return len(_sentences(text)) <= val
    if ctype == "json_valid":
        try:
            json.loads(text)
            return True
        except json.JSONDecodeError:
            # tolerate a fenced block, a common model formatting choice;
            # the fence itself violates "no text outside JSON" only if the
            # instruction said so — that stricter reading is a SOFT call.
            m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
            if m:
                try:
                    json.loads(m.group(1))
                    return True
                except json.JSONDecodeError:
                    return False
            return False
    if ctype == "question_count":
        return sum(1 for s in _sentences(text) if s.rstrip().endswith("?")) == val
    raise ValueError(f"unknown check type: {ctype}")


def verify_response(instruction, response):
    """All hard-constraint verdicts for one (instruction, response) pair."""
    out = {}
    for con in instruction["constraints"]:
        if con["kind"] == "hard":
            out[con["cid"]] = check(response, con["check"])
    return out
