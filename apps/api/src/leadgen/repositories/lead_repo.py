from uuid import UUID
from sqlalchemy.orm import Session
from leadgen.models.lead import Lead
from leadgen.models.company import Company
from leadgen.models.interaction import Interaction
from leadgen.schemas.lifecycle import LifecycleState


class LeadRepo:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_company(self, *, name: str, domain: str | None = None) -> Company:
        query = self.db.query(Company)
        if domain:
            existing = query.filter(Company.domain == domain).first()
            if existing:
                return existing
        existing = query.filter(Company.name == name).first()
        if existing:
            return existing
        company = Company(name=name, domain=domain)
        self.db.add(company)
        self.db.flush()
        return company

    def create_lead(self, *, company_id: UUID, profile_id: str) -> Lead:
        lead = Lead(company_id=company_id, profile_id=profile_id, state=LifecycleState.NEW)
        self.db.add(lead)
        self.db.flush()
        return lead

    def update_state(self, lead: Lead, new_state: LifecycleState) -> None:
        from leadgen.schemas.lifecycle import can_transition
        if not can_transition(lead.state, new_state):
            raise ValueError(f"Invalid transition: {lead.state} → {new_state}")
        lead.state = new_state
        self.db.flush()

    def save_interaction(self, interaction: dict) -> None:
        record = Interaction(**interaction)
        self.db.add(record)
        self.db.flush()

    def update_enrichment(self, company: Company, dossier: str) -> None:
        company.enrichment = {"dossier": dossier}
        self.db.flush()

    def update_icp_match(self, lead: Lead, icp_match: dict) -> None:
        lead.icp_match = icp_match
        self.db.flush()

    def update_score(self, lead: Lead, score: int, reasoning: str) -> None:
        lead.score = float(score)
        lead.score_reasoning = reasoning
        self.db.flush()
