from pydantic import BaseModel, Field


class IcpMatchResult(BaseModel):
    """LLM-produced ICP fit analysis. reasoning field first forces chain-of-thought before deciding."""

    reasoning: str = Field(description="2-4 sentence explanation of fit assessment")
    is_match: bool = Field(description="Whether this company meets the ICP filters")
    fit_signals: list[str] = Field(description="Positive signals found (max 5)")
    miss_signals: list[str] = Field(description="Negative signals or missing data (max 5)")
    confidence: float = Field(ge=0, le=1, description="Confidence in the assessment")
