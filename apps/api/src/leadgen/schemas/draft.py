from pydantic import BaseModel, Field


class DraftMessage(BaseModel):
    """Personalized outreach draft with citations to company-specific facts used."""

    reasoning: str = Field(description="Why this opener should land with this company")
    subject: str = Field(max_length=80)
    body: str = Field(max_length=800, description="Plain text, under 120 words")
    hooks_used: list[str] = Field(description="Specific facts from enrichment that the draft cites")
    tone_check: str = Field(description="Self-assessment: does this match the profile's tone?")
