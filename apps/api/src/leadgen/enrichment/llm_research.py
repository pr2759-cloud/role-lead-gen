"""Company research via Claude with the web_search tool.

Returns a dossier (markdown text) summarizing: what the company does,
recent funding/news, hiring activity, technical signals, and any
recent posts or launches that could become outreach hooks.
"""
import time
import anthropic
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from leadgen.config import settings
from leadgen.observability.llm_metering import calculate_cost

RESEARCH_PROMPT_VERSION = "research_v1"

RESEARCH_SYSTEM = """You are a research analyst. Search for a company and write a SHORT dossier for outreach personalization.

Run 1-2 web searches maximum. Write under 300 words total. Be specific, no filler.

Cover only what you find evidence for:
- What they do (1 sentence)
- Stage/funding (latest round + amount)
- Open roles matching: FDE, GTM Engineer, Solutions Engineer, Applied AI Engineer, Customer Engineer
- One specific recent hook (launch, blog post, or news from last 90 days — quote it)
- One tech/culture signal

If a section has no evidence, skip it entirely. No invented facts."""


class EnrichmentResult(BaseModel):
    company_name: str
    domain: str | None
    dossier: str
    cost_usd: float
    latency_ms: int


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=30, max=90),
    retry=retry_if_exception_type((anthropic.APIConnectionError, anthropic.RateLimitError)),
)
def research_company(*, name: str, domain: str | None = None) -> tuple[EnrichmentResult, dict]:
    """Run Claude with web_search to produce a company dossier."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    model = "claude-haiku-4-5-20251001"

    user_msg = f"Company: {name}"
    if domain:
        user_msg += f"\nDomain: {domain}"
    user_msg += "\n\nProduce the dossier."

    start = time.perf_counter()
    response = client.messages.create(
        model=model,
        max_tokens=600,
        system=RESEARCH_SYSTEM,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 2}],
        messages=[{"role": "user", "content": user_msg}],
    )
    latency_ms = int((time.perf_counter() - start) * 1000)

    dossier_parts = [b.text for b in response.content if b.type == "text"]  # type: ignore[union-attr]
    dossier = "\n\n".join(dossier_parts).strip()

    cost = calculate_cost(model, response.usage.input_tokens, response.usage.output_tokens)

    result = EnrichmentResult(
        company_name=name,
        domain=domain,
        dossier=dossier,
        cost_usd=cost,
        latency_ms=latency_ms,
    )
    interaction = {
        "kind": "research",
        "prompt_version": RESEARCH_PROMPT_VERSION,
        "model": model,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cost_usd": cost,
        "latency_ms": latency_ms,
        "request": {"system": RESEARCH_SYSTEM, "user": user_msg},
        "response": {"dossier": dossier},
    }
    return result, interaction
