from uuid import UUID, uuid4
from sqlalchemy import ForeignKey, Float, Text, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID, JSONB, ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column
from leadgen.models.base import Base, TimestampMixin
from leadgen.schemas.lifecycle import LifecycleState


lifecycle_enum = PgEnum(
    LifecycleState,
    name="lifecycle_state",
    values_callable=lambda enum: [e.value for e in enum],
    create_type=True,
)


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    contact_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("contacts.id"))

    state: Mapped[LifecycleState] = mapped_column(lifecycle_enum, nullable=False, default=LifecycleState.NEW, index=True)

    icp_match: Mapped[dict | None] = mapped_column(JSONB)
    score: Mapped[float | None] = mapped_column(Float)
    score_reasoning: Mapped[str | None] = mapped_column(Text)

    profile_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
