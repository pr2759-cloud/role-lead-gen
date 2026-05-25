from uuid import UUID
from leadgen.reasoning.llm import LLMClient
from leadgen.reasoning.prompts import score_v1
from leadgen.schemas.score import LeadScore
from leadgen.schemas.icp import IcpMatchResult
from leadgen.schemas.profile import Profile


def score_lead(
    *,
    profile: Profile,
    company_dossier: str,
    icp_match: IcpMatchResult,
    llm: LLMClient,
    lead_id: UUID | None = None,
) -> tuple[LeadScore, dict]:
    candidate_summary = _summarize_candidate(profile)
    system = score_v1.SYSTEM.format(candidate_name=profile.candidate.name)
    user = score_v1.build_user_prompt(
        candidate_summary=candidate_summary,
        company_dossier=company_dossier,
        icp_match_result=icp_match.model_dump(),
    )
    return llm.structured(
        system=system,
        user=user,
        output_schema=LeadScore,
        kind="score",
        prompt_version=score_v1.PROMPT_VERSION,
        lead_id=lead_id,
    )


def _summarize_candidate(profile: Profile) -> str:
    lines = [
        f"Name: {profile.candidate.name}",
        f"Current role: {profile.candidate.current_role}",
        "Background:",
        *[f"  - {b}" for b in profile.candidate.background],
        "Superpowers:",
        *[f"  - {s}" for s in profile.candidate.superpowers],
        f"Target roles: {', '.join(profile.target_roles)}",
    ]
    return "\n".join(lines)
