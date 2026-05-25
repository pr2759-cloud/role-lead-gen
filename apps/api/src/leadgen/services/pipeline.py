"""End-to-end pipeline for one company: enrich → match → score → draft.

Each stage persists its outputs and writes an interaction row. State
transitions mark progress. Failures leave the lead in its last-good state.
"""
from dataclasses import dataclass
import structlog
from sqlalchemy.orm import Session

from leadgen.schemas.profile import Profile
from leadgen.schemas.lifecycle import LifecycleState
from leadgen.schemas.icp import IcpMatchResult
from leadgen.schemas.score import LeadScore, ScoreDimension
from leadgen.schemas.draft import DraftMessage
from leadgen.schemas.analysis import CompanyAnalysis
from leadgen.reasoning.llm import LLMClient
from leadgen.reasoning.prompts import analyze_v1, draft_v1
from leadgen.reasoning.scorer import _summarize_candidate
from leadgen.reasoning.personalizer import draft_opener
from leadgen.enrichment.llm_research import research_company
from leadgen.repositories.lead_repo import LeadRepo

# Dossier chars passed to reasoning calls — keeps prompts under ~2k tokens.
DOSSIER_CHAR_LIMIT = 2000

log = structlog.get_logger()


@dataclass
class LeadResult:
    company_name: str
    icp_match: IcpMatchResult | None
    score: LeadScore | None
    draft: DraftMessage | None
    total_cost_usd: float
    error: str | None = None


class Pipeline:
    def __init__(self, *, db: Session, profile: Profile, profile_id: str):
        self.db = db
        self.profile = profile
        self.profile_id = profile_id
        self.repo = LeadRepo(db)
        self.llm = LLMClient()

    def run_for_company(self, *, name: str, domain: str | None = None) -> LeadResult:
        log.info("pipeline.start", company=name)
        company = self.repo.get_or_create_company(name=name, domain=domain)
        lead = self.repo.create_lead(company_id=company.id, profile_id=self.profile_id)
        total_cost = 0.0

        try:
            # Stage 1: enrich — skip if company already has a dossier in DB
            if company.enrichment and company.enrichment.get("dossier"):
                dossier = company.enrichment["dossier"]
                log.info("pipeline.enrich_cached", company=name)
            else:
                enrichment, research_interaction = research_company(name=name, domain=domain)
                research_interaction["lead_id"] = lead.id
                self.repo.save_interaction(research_interaction)
                self.repo.update_enrichment(company, enrichment.dossier)
                total_cost += enrichment.cost_usd
                dossier = enrichment.dossier
                self.db.commit()

            self.repo.update_state(lead, LifecycleState.ENRICHED)
            self.db.commit()

            # Truncate for LLM calls — full dossier stays in DB
            dossier_for_llm = dossier[:DOSSIER_CHAR_LIMIT]

            # Stage 2: ICP match + score in one haiku call
            system = analyze_v1.SYSTEM.format(candidate_name=self.profile.candidate.name)
            user = analyze_v1.build_user_prompt(
                icp_dict=self.profile.icp.model_dump(),
                candidate_summary=_summarize_candidate(self.profile),
                company_dossier=dossier_for_llm,
            )
            analysis, analysis_interaction = self.llm.structured_fast(
                system=system,
                user=user,
                output_schema=CompanyAnalysis,
                kind="analyze",
                prompt_version=analyze_v1.PROMPT_VERSION,
                lead_id=lead.id,
                max_tokens=800,
            )
            self.repo.save_interaction(analysis_interaction)
            total_cost += analysis_interaction["cost_usd"]

            # Convert CompanyAnalysis → IcpMatchResult + LeadScore for DB + result
            icp_result = IcpMatchResult(
                reasoning=analysis.reasoning,
                is_match=analysis.is_match,
                fit_signals=analysis.fit_signals,
                miss_signals=analysis.miss_signals,
                confidence=0.8,
            )
            self.repo.update_icp_match(lead, icp_result.model_dump(mode="json"))

            if not analysis.is_match:
                self.repo.update_state(lead, LifecycleState.REJECTED)
                self.db.commit()
                log.info("pipeline.rejected_at_icp", company=name, cost=total_cost)
                return LeadResult(company.name, icp_result, None, None, total_cost)

            score = LeadScore(
                reasoning=analysis.reasoning,
                dimensions=[
                    ScoreDimension(name=d.name, score=d.score, weight=d.weight, reasoning="")
                    for d in analysis.dimensions
                ],
                composite=analysis.composite,
                tier=analysis.tier,
            )
            self.repo.update_score(lead, score.composite, score.reasoning)
            self.repo.update_state(lead, LifecycleState.SCORED)

            # Stage 3: draft (sonnet — quality matters here)
            draft, draft_interaction = draft_opener(
                profile=self.profile, company_dossier=dossier_for_llm, llm=self.llm, lead_id=lead.id,
            )
            self.repo.save_interaction(draft_interaction)
            self.repo.update_state(lead, LifecycleState.AWAITING_REVIEW)
            total_cost += draft_interaction["cost_usd"]

            self.db.commit()
            log.info("pipeline.complete", company=name, score=score.composite, cost=total_cost)
            return LeadResult(company.name, icp_result, score, draft, total_cost)

        except Exception as exc:
            self.db.rollback()
            log.exception("pipeline.failed", company=name)
            return LeadResult(company.name, None, None, None, total_cost, error=str(exc))
