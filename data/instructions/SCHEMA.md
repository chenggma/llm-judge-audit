# Instruction schema

One JSON object per line (`*.jsonl`). All instructions are authored for this
study (no verbatim copies from public benchmarks).

```json
{
  "id": "inst-0001",
  "domain": "professional-writing",       // professional-writing | explanation | planning | technical | analysis | creative
  "prompt": "…the full instruction shown to generator models…",
  "constraints": [
    {
      "cid": "c1",
      "text": "human-readable statement of the constraint",
      "kind": "hard",                      // hard = machine-verifiable, soft = judgment
      "check": {"type": "word_count_max", "value": 150}   // hard only
    },
    {"cid": "c2", "text": "…", "kind": "soft"}
  ]
}
```

Hard check types implemented in `src/verify_hard.py`:

| type | value | passes iff |
|---|---|---|
| `word_count_max` / `word_count_min` | int | whitespace-token count ≤ / ≥ value |
| `bullet_count` | int | exactly value lines starting with `-`, `*`, or `•` |
| `numbered_items` | int | exactly value lines starting `1.` `2.` … in order |
| `paragraph_count` | int | exactly value blank-line-separated blocks |
| `contains` | string | value appears verbatim (case-insensitive) |
| `not_contains` | string | value absent (case-insensitive, word-boundary) |
| `section_headers` | [str,…] | every listed markdown header present, in order |
| `starts_with` | string | first non-whitespace chars match (case-sensitive) |
| `ends_with` | string | last non-whitespace chars match (case-sensitive) |
| `sentence_count_max` | int | naive sentence split count ≤ value |
| `json_valid` | true | entire response parses as JSON |
| `question_count` | int | exactly value sentences ending in `?` |

Authoring rules:
- 4–6 constraints per instruction; 2–3 hard + 2–3 soft.
- Constraints must be *individually* checkable and non-redundant.
- Soft constraints must be things two careful readers usually agree on
  (pilot κ will verify).
- The prompt states every constraint explicitly — no hidden requirements.
