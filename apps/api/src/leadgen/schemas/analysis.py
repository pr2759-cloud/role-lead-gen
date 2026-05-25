from pydantic import BaseModel, Field


class SlimDimension(BaseModel):
    name: str
    score: int = Field(ge=0, le=100)
    weight: float = Field(ge=0, le=1)


class CompanyAnalysis(BaseModel):
    """Combined ICP match + score in one LLM call to save tokens."""
    reasoning: str  # first so truncation hits less critical fields
    is_match: bool
    tier: str
    composite: int = Field(ge=0, le=100)
    fit_signals: list[str]
    miss_signals: list[str]
    dimensions: list[SlimDimension]
