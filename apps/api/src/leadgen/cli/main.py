import typer
from rich.console import Console
from pydantic import BaseModel
from leadgen.reasoning.llm import LLMClient

app = typer.Typer(no_args_is_help=True)
console = Console()


class PingResponse(BaseModel):
    greeting: str
    confidence: float


@app.command()
def ping():
    """Smoke test the LLM client."""
    client = LLMClient()
    result, interaction = client.structured(
        system="You are a friendly assistant.",
        user="Say hello and rate your confidence 0-1.",
        output_schema=PingResponse,
        kind="ping",
        prompt_version="ping_v1",
    )
    console.print(f"[green]✓[/green] LLM responded: {result.greeting}")
    console.print(f"  Cost: ${interaction['cost_usd']:.6f} | Latency: {interaction['latency_ms']}ms")


@app.command()
def research(
    name: str = typer.Argument(..., help="Company name"),
    domain: str = typer.Option(None, help="Company domain"),
):
    """Smoke test: research one company and print the dossier."""
    from leadgen.enrichment.llm_research import research_company
    result, interaction = research_company(name=name, domain=domain)
    console.print(f"\n[bold]Dossier for {result.company_name}[/bold]\n")
    console.print(result.dossier)
    console.print(f"\n[dim]Cost: ${result.cost_usd:.4f} | Latency: {result.latency_ms}ms[/dim]")


if __name__ == "__main__":
    app()
