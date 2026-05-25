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

RESEARCH_SYSTEM = """You are a research analyst. Given a company name and optional domain, produce a concise dossier suitable for outreach personalization.

Use web_search to find current information. Structure the dossier with these sections (skip any you can't find evidence for):

## What they do
1-2 sentences on product and target customer.

## Stage and traction
Latest funding round, headcount range, notable customers. Cite sources where possible.

## Hiring signals
Currently open roles, especially for FDE, GTM Engineer, Solutions Engineer, Applied AI Engineer, Customer Engineer. Quote the role title.

## Recent moves
Launches, integrations, blog posts, or public statements from the last 90 days that could become a specific opener hook.

## Technical and culture signals
Engineering blog presence, tech stack mentions, design-doc culture, or notable technical decisions.

Be specific. Quote exact phrases where they would make a strong opener. If you can't find information for a section, write "No public signal found" — do NOT invent facts."""


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
    model = "claude-sonnet-4-6"

    user_msg = f"Company: {name}"
    if domain:
        user_msg += f"\nDomain: {domain}"
    user_msg += "\n\nProduce the dossier."

    start = time.perf_counter()
    response = client.messages.create(
        model=model,
        max_tokens=1500,
        system=RESEARCH_SYSTEM,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
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
