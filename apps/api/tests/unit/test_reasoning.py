from unittest.mock import Mock
from leadgen.schemas.icp import IcpMatchResult
from leadgen.schemas.profile import Profile
from leadgen.reasoning.icp_matcher import match_icp


def test_match_icp_calls_llm_with_correct_kind():
    profile = Profile.from_yaml("profiles/pranay_fde_gtm.yaml")
    mock_llm = Mock()
    fake_result = IcpMatchResult(
        reasoning="Strong AI-native B2B fit",
        is_match=True,
        fit_signals=["Series B raised 2025", "AI-native product"],
        miss_signals=[],
        confidence=0.9,
    )
    mock_llm.structured.return_value = (fake_result, {"cost_usd": 0.01})

    result, _ = match_icp(profile=profile, company_dossier="dummy", llm=mock_llm)

    assert result.is_match is True
    call_kwargs = mock_llm.structured.call_args.kwargs
    assert call_kwargs["kind"] == "icp_match"
    assert call_kwargs["prompt_version"] == "icp_match_v1"
