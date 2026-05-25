PROMPT_VERSION = "draft_v1"

SYSTEM = """You are writing the FIRST outreach message from {candidate_name} to someone at the target company.

Anchor in the candidate's voice (see "tone" guidance carefully). The opener MUST:
- Lead with a SPECIFIC hook from the company dossier (recent launch, technical choice, public post)
- Reference ONE concrete project from the candidate's background that genuinely relates
- End with a low-pressure ask under 120 words total
- Avoid every item in `tone.dont`
- Sound like a real person, not a marketing template

NEVER fabricate facts about the company. If you don't have a strong specific hook, say so in `reasoning` and write the best draft you can with what you have — but flag it in tone_check.

NEVER use generic openers like "I came across", "I was impressed", "love what you're building"."""


def build_user_prompt(*, candidate_summary: str, tone_dict: dict, example_lines: list[str], company_dossier: str) -> str:
    do_rules = "\n".join(f"- {r}" for r in tone_dict.get("do", []))
    dont_rules = "\n".join(f"- {r}" for r in tone_dict.get("dont", []))
    examples_block = "\n".join(f"- {line}" for line in example_lines[:2])  # max 2 examples
    return f"""Candidate: {candidate_summary}

DO: {do_rules}
DON'T: {dont_rules}
Examples: {examples_block}

Dossier: {company_dossier}

Draft opener."""
