#!/usr/bin/env python3
# score.py — CLI: score and rank every song in library_scan.json.
# Usage: python ml/difficulty_scorer/score.py [LIBRARY_JSON]

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich import box

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from ml.difficulty_scorer.scorer import load_tiers, score_library

console = Console()
PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_LIBRARY   = str(PROJECT_ROOT / "data" / "library_scan.json")
DEFAULT_TECHNIQUES = str(PROJECT_ROOT / "data" / "techniques.json")


def difficulty_color(score: float) -> str:
    if score >= 8:   return "bold red"
    if score >= 6:   return "yellow"
    if score >= 4:   return "green"
    return "dim"


@click.command()
@click.argument("library_json", default=DEFAULT_LIBRARY,
                type=click.Path(exists=True))
@click.option("--techniques", default=DEFAULT_TECHNIQUES, show_default=True,
              type=click.Path(exists=True))
@click.option("--output", "-o", default=None,
              help="Save scored results to this JSON file.")
@click.option("--detail", "-d", is_flag=True,
              help="Show per-component score breakdown.")
def main(library_json, techniques, output, detail):
    """Score and rank every song in LIBRARY_JSON by difficulty (1-10)."""
    with open(library_json) as f:
        entries = json.load(f)

    tiers  = load_tiers(techniques)
    ranked = score_library(entries, tiers)

    table = Table(title="Library — Ranked by Difficulty", box=box.SIMPLE_HEAD)
    table.add_column("Rank", justify="right", style="dim", width=4)
    table.add_column("Song", style="bold", max_width=42)
    table.add_column("BPM", justify="right")
    table.add_column("Body", justify="right", width=5)
    table.add_column("Peak", justify="right", width=5)
    if detail:
        table.add_column("BPM", justify="right", style="dim", width=5)
        table.add_column("D-body", justify="right", style="dim", width=6)
        table.add_column("D-peak", justify="right", style="dim", width=6)
        table.add_column("Technique", justify="right", style="dim", width=9)
        table.add_column("Diversity", justify="right", style="dim", width=9)

    for rank, entry in enumerate(ranked, 1):
        d          = entry["difficulty"]
        c          = d["components"]
        body_score = d["body_score"]
        peak_score = d["peak_score"]
        label      = entry["title"] or entry["filename"]
        row = [
            str(rank), label, str(entry["bpm"]),
            f"[{difficulty_color(body_score)}]{body_score}[/]",
            f"[{difficulty_color(peak_score)}]{peak_score}[/]",
        ]
        if detail:
            row += [f"{c['bpm']:.2f}", f"{c['density_body']:.2f}", f"{c['density_peak']:.2f}",
                    f"{c['technique']:.2f}", f"{c['diversity']:.2f}"]
        table.add_row(*row)

    console.print(table)

    if output:
        Path(output).write_text(json.dumps(ranked, indent=2))
        console.print(f"\n[green]Saved scored results to:[/] {output}")


if __name__ == "__main__":
    main()
