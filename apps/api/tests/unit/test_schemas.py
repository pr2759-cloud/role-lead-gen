import pytest
from pydantic import ValidationError
from leadgen.schemas.score import LeadScore, ScoreDimension


def test_lead_score_requires_dimensions():
    with pytest.raises(ValidationError):
        LeadScore(reasoning="test", dimensions=[], composite=50, tier="weak_fit")


def test_lead_score_composite_clamped():
    with pytest.raises(ValidationError):
        LeadScore(
            reasoning="x",
            dimensions=[
                ScoreDimension(name="a", score=50, weight=0.5, reasoning="r"),
                ScoreDimension(name="b", score=50, weight=0.5, reasoning="r"),
                ScoreDimension(name="c", score=50, weight=0.0, reasoning="r"),
            ],
            composite=150,
            tier="strong_fit",
        )
