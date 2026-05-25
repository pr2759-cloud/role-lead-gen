import csv
import json
from datetime import datetime
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from pydantic import BaseModel
from sqlalchemy.orm import Session

from leadgen.db import SessionLocal
from leadgen.schemas.profile import Profile
from leadgen.services.pipeline import Pipeline, LeadResult
from leadgen.observability.logging import configure_logging
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


@app.command()
def run(
    csv_path: Path = typer.Option(..., "--csv", help="Path to seed CSV with name,domain"),
    profile_path: Path = typer.Option(..., "--profile", help="Path to profile YAML"),
    output_dir: Path = typer.Option(Path("data/output"), "--output-dir"),
):
    """Run the full pipeline against a CSV of seed companies."""
    configure_logging()
    profile = Profile.from_yaml(str(profile_path))
    profile_id = profile_path.stem

    console.print(f"[green]✓[/green] Loaded profile: [bold]{profile_id}[/bold]")
    console.print(f"  Targets: {', '.join(profile.target_roles)}")
    console.print(f"  Stages: {', '.join(profile.icp.company_stage)}\n")

    with open(csv_path) as f:
        rows = list(csv.DictReader(f))
    console.print(f"[green]✓[/green] Ingested {len(rows)} companies from CSV\n")

    db: Session = SessionLocal()
    pipeline = Pipeline(db=db, profile=profile, profile_id=profile_id)
    results: list[LeadResult] = []

    for i, row in enumerate(rows, start=1):
        import time as _time
        if i > 1:
            _time.sleep(45)  # respect 30k input tokens/min rate limit between companies
        name = row["name"].strip()
        domain = row.get("domain", "").strip() or None
        console.print(f"[bold cyan][{i}/{len(rows)}] {name}[/bold cyan]")
        result = pipeline.run_for_company(name=name, domain=domain)
        results.append(result)

        if result.error:
            console.print(f"  [red]✗ failed: {result.error}[/red]\n")
            continue
        if not result.icp_match or not result.icp_match.is_match:
            console.print(f"  [yellow]✗ disqualified at ICP[/yellow]\n")
            continue
        assert result.score is not None and result.draft is not None
        console.print(f"  [green]✓[/green] scored {result.score.composite}/100 — {result.score.tier}")
        console.print(f"  [green]✓[/green] drafted ({len(result.draft.body)} chars)")
        console.print(f"  [dim]cost: ${result.total_cost_usd:.4f}[/dim]\n")

    db.close()
    _print_summary(results)
    _write_report(results, output_dir)


def _print_summary(results: list[LeadResult]) -> None:
    table = Table(title="Run summary")
    table.add_column("Company")
    table.add_column("ICP", justify="center")
    table.add_column("Score", justify="right")
    table.add_column("Tier")
    table.add_column("Cost", justify="right")
    for r in results:
        icp = "✓" if r.icp_match and r.icp_match.is_match else "✗"
        score = str(r.score.composite) if r.score else "-"
        tier = r.score.tier if r.score else "-"
        table.add_row(r.company_name, icp, score, tier, f"${r.total_cost_usd:.4f}")
    console.print(table)

    total = sum(r.total_cost_usd for r in results)
    qualified = sum(1 for r in results if r.icp_match and r.icp_match.is_match)
    console.print(f"\n[bold]Total LLM cost:[/bold] ${total:.4f}")
    console.print(f"[bold]Qualified:[/bold] {qualified}/{len(results)}")


def _write_report(results: list[LeadResult], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    path = output_dir / f"run_{ts}.json"
    payload = [
        {
            "company": r.company_name,
            "icp_match": r.icp_match.model_dump(mode="json") if r.icp_match else None,
            "score": r.score.model_dump(mode="json") if r.score else None,
            "draft": r.draft.model_dump(mode="json") if r.draft else None,
            "cost_usd": r.total_cost_usd,
            "error": r.error,
        }
        for r in results
    ]
    path.write_text(json.dumps(payload, indent=2))
    console.print(f"\n[dim]Report written to {path}[/dim]")


if __name__ == "__main__":
    app()
