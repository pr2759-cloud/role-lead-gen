from typing import Literal
from pydantic import BaseModel, Field


class Candidate(BaseModel):
    name: str
    current_role: str
    background: list[str] = Field(min_length=1)
    superpowers: list[str] = Field(min_length=1, description="What makes you hireable")


class IcpFilters(BaseModel):
    company_stage: list[Literal["pre-seed", "seed", "series-a", "series-b", "series-c", "series-d-plus", "public"]]
    must_be_hiring_for: list[str] = Field(min_length=1, description="Role families to filter on")
    prefers: list[str] = Field(default_factory=list, description="Soft positive signals")
    disqualifies: list[str] = Field(default_factory=list, description="Hard negative signals")


class Tone(BaseModel):
    voice: str = Field(description="3-5 adjectives describing your voice")
    do: list[str] = Field(default_factory=list)
    dont: list[str] = Field(default_factory=list)
    example_lines: list[str] = Field(
        default_factory=list,
        description="Few-shot examples of how you write openers",
    )


class Profile(BaseModel):
    """Top-level user profile loaded from YAML."""
    schema_version: int = 1
    candidate: Candidate
    target_roles: list[str] = Field(min_length=1)
    icp: IcpFilters
    tone: Tone

    @classmethod
    def from_yaml(cls, path: str) -> "Profile":
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)
