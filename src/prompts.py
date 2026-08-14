"""Judge elicitation prompts. FROZEN at protocol freeze; the paraphrase
variants for the rubric-sensitivity sub-study live at the bottom and are
frozen too."""

RUBRIC_JUDGE = """You are evaluating whether a response follows an instruction.

INSTRUCTION:
{instruction}

RESPONSE:
{response}

CONSTRAINTS to evaluate, each with an id:
{constraint_list}

For each constraint decide: "sat" (fully satisfied), "unsat" (not or only
partially satisfied), or "cant_tell". Partial compliance is "unsat".
Then give a holistic quality score 1-5 for the response as an answer to the
instruction (5 = flawless and useful, 3 = useful but a notable miss,
1 = ignores the instruction), and your confidence 0-100 that your verdicts
match what a careful human annotator would say.

Answer in valid JSON only:
{{"verdicts": {{"<cid>": "sat|unsat|cant_tell", ...}},
  "holistic": <1-5>, "confidence": <0-100>}}"""

BARE_JUDGE = """You are evaluating whether a response follows an instruction.

INSTRUCTION:
{instruction}

RESPONSE:
{response}

Give a holistic quality score 1-5 for the response as an answer to the
instruction (5 = flawless and useful, 3 = useful but a notable miss,
1 = ignores the instruction), and your confidence 0-100 that your score
matches what a careful human annotator would give.

Answer in valid JSON only:
{{"holistic": <1-5>, "confidence": <0-100>}}"""

PAIRWISE_JUDGE = """Two responses to the same instruction. Decide which better
follows the instruction, considering every explicit requirement.

INSTRUCTION:
{instruction}

RESPONSE A:
{response_a}

RESPONSE B:
{response_b}

Prefer the response satisfying more explicit requirements; break ties on
content quality; answer "tie" only if genuinely equal.

Answer in valid JSON only:
{{"winner": "A|B|tie", "confidence": <0-100>}}"""

# Paraphrase variants for rubric-sensitivity (same meaning, different words).
RUBRIC_JUDGE_PARA = """Your task: check a response against an instruction's
requirements.

INSTRUCTION:
{instruction}

RESPONSE:
{response}

Requirements to check, each with an id:
{constraint_list}

Mark each requirement "sat" if the response meets it completely, "unsat" if
it misses or only partly meets it, or "cant_tell" if the text alone cannot
settle it. Then rate overall quality 1-5 (5 = nothing to fix, 3 = has a
clear miss but useful, 1 = fails to address the instruction) and state
confidence 0-100 that a careful human would agree with you.

Reply with JSON only:
{{"verdicts": {{"<cid>": "sat|unsat|cant_tell", ...}},
  "holistic": <1-5>, "confidence": <0-100>}}"""
