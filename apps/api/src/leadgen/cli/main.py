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


if __name__ == "__main__":
    app()
