from uuid import UUID, uuid4
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column
from leadgen.models.base import Base, TimestampMixin


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    lead_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True)
    subject: Mapped[str | None] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False, default="email")
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # "outbound" | "inbound"
