from uuid import UUID
from leadgen.reasoning.llm import LLMClient
from leadgen.reasoning.prompts import draft_v1
from leadgen.schemas.draft import DraftMessage
from leadgen.schemas.profile import Profile
from leadgen.reasoning.scorer import _summarize_candidate


def draft_opener(
    *,
    profile: Profile,
    company_dossier: str,
    llm: LLMClient,
    lead_id: UUID | None = None,
) -> tuple[DraftMessage, dict]:
    system = draft_v1.SYSTEM.format(candidate_name=profile.candidate.name)
    user = draft_v1.build_user_prompt(
        candidate_summary=_summarize_candidate(profile),
        tone_dict=profile.tone.model_dump(),
        example_lines=profile.tone.example_lines,
        company_dossier=company_dossier,
    )
    return llm.structured(
        system=system,
        user=user,
        output_schema=DraftMessage,
        kind="draft",
        prompt_version=draft_v1.PROMPT_VERSION,
        lead_id=lead_id,
        max_tokens=400,
    )
