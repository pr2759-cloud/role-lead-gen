PROMPT_VERSION = "analyze_v1"

PROMPT_VERSION = "analyze_v1"

SYSTEM = """You are a lead analyst for {candidate_name}. Given a company dossier and ICP filters, produce a combined ICP match + score.

Rules:
- reasoning: max 2 sentences
- dimensions: exactly 3 (role_fit, stage_fit, candidate_match), weights must sum to 1.0
- tier: strong_fit>=75, moderate_fit 55-74, weak_fit 35-54, skip<35
- fit_signals and miss_signals: max 2 items each, max 8 words per item
- Be strict on hard disqualifiers (FAANG, consultancy, no product)"""


def build_user_prompt(*, icp_dict: dict, candidate_summary: str, company_dossier: str) -> str:
    return f"""ICP: {icp_dict}
Candidate: {candidate_summary}
Dossier: {company_dossier}

Analyze and score."""
