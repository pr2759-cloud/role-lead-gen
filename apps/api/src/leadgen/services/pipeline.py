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
from leadgen.schemas.score import LeadScore
from leadgen.schemas.draft import DraftMessage
from leadgen.reasoning.llm import LLMClient
from leadgen.reasoning.icp_matcher import match_icp
from leadgen.reasoning.scorer import score_lead
from leadgen.reasoning.personalizer import draft_opener
from leadgen.enrichment.llm_research import research_company
from leadgen.repositories.lead_repo import LeadRepo

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
            # Stage 1: enrich
            enrichment, research_interaction = research_company(name=name, domain=domain)
            research_interaction["lead_id"] = lead.id
            self.repo.save_interaction(research_interaction)
            self.repo.update_enrichment(company, enrichment.dossier)
            self.repo.update_state(lead, LifecycleState.ENRICHED)
            total_cost += enrichment.cost_usd

            # Stage 2: ICP match
            icp_result, icp_interaction = match_icp(
                profile=self.profile, company_dossier=enrichment.dossier, llm=self.llm, lead_id=lead.id,
            )
            self.repo.save_interaction(icp_interaction)
            self.repo.update_icp_match(lead, icp_result.model_dump(mode="json"))
            total_cost += icp_interaction["cost_usd"]

            if not icp_result.is_match:
                self.repo.update_state(lead, LifecycleState.REJECTED)
                self.db.commit()
                log.info("pipeline.rejected_at_icp", company=name, cost=total_cost)
                return LeadResult(company.name, icp_result, None, None, total_cost)

            # Stage 3: score
            score, score_interaction = score_lead(
                profile=self.profile,
                company_dossier=enrichment.dossier,
                icp_match=icp_result,
                llm=self.llm,
                lead_id=lead.id,
            )
            self.repo.save_interaction(score_interaction)
            self.repo.update_score(lead, score.composite, score.reasoning)
            self.repo.update_state(lead, LifecycleState.SCORED)
            total_cost += score_interaction["cost_usd"]

            # Stage 4: draft
            draft, draft_interaction = draft_opener(
                profile=self.profile, company_dossier=enrichment.dossier, llm=self.llm, lead_id=lead.id,
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
