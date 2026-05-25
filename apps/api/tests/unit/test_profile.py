from leadgen.schemas.profile import Profile


def test_profile_loads(tmp_path):
    """Profile YAML round-trips through Pydantic validation."""
    profile = Profile.from_yaml("profiles/pranay_fde_gtm.yaml")
    assert profile.candidate.name == "Pranay Rawat"
    assert len(profile.target_roles) >= 1
    assert "series-a" in profile.icp.company_stage
