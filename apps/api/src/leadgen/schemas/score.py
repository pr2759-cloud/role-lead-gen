from pydantic import BaseModel, Field


class ScoreDimension(BaseModel):
    name: str
    score: int = Field(ge=0, le=100)
    weight: float = Field(ge=0, le=1)
    reasoning: str


class LeadScore(BaseModel):
    """Multi-factor lead score. Composite is a weighted average of dimensions."""

    reasoning: str = Field(description="Overall scoring rationale, 2-4 sentences")
    dimensions: list[ScoreDimension] = Field(min_length=3, max_length=6)
    composite: int = Field(ge=0, le=100, description="Final weighted score 0-100")
    tier: str = Field(description="One of: strong_fit | moderate_fit | weak_fit | skip")
