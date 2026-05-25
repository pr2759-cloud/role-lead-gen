from uuid import UUID
from leadgen.reasoning.llm import LLMClient
from leadgen.reasoning.prompts import icp_match_v1
from leadgen.schemas.icp import IcpMatchResult
from leadgen.schemas.profile import Profile


def match_icp(
    *,
    profile: Profile,
    company_dossier: str,
    llm: LLMClient,
    lead_id: UUID | None = None,
) -> tuple[IcpMatchResult, dict]:
    system = icp_match_v1.SYSTEM.format(candidate_name=profile.candidate.name)
    user = icp_match_v1.build_user_prompt(
        icp_dict=profile.icp.model_dump(),
        company_dossier=company_dossier,
    )
    return llm.structured(
        system=system,
        user=user,
        output_schema=IcpMatchResult,
        kind="icp_match",
        prompt_version=icp_match_v1.PROMPT_VERSION,
        lead_id=lead_id,
    )
