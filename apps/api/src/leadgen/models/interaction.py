from uuid import UUID, uuid4
from sqlalchemy import String, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PgUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from leadgen.models.base import Base, TimestampMixin


class Interaction(Base, TimestampMixin):
    """Every LLM call logged. Drives cost tracking and prompt evals."""
    __tablename__ = "interactions"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    lead_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("leads.id"), index=True)

    kind: Mapped[str] = mapped_column(String(50), nullable=False)  # "icp_match" | "score" | "draft" | "research"
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False)

    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    request: Mapped[dict] = mapped_column(JSONB)
    response: Mapped[dict] = mapped_column(JSONB)
