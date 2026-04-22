#!/usr/bin/env python3
# explore_library.py — Walk a folder of Guitar Pro files and produce a summary table + JSON.
# Usage: python scripts/explore_library.py path/to/tabs/folder

import json
import sys
from pathlib import Path

import click
import guitarpro
from rich.console import Console
from rich.table import Table
from rich import box
from rich.progress import track as rich_track

console = Console()
GP_EXTENSIONS = {".gp", ".gpx", ".gp5", ".gp4", ".gp3"}


def fix_enc(s: str) -> str:
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return s

TECHNIQUE_FLAGS = {
    "bend":      lambda n: n.bend is not None and n.bend.points,
    "vibrato":   lambda n: n.effect.vibrato,
    "slide":     lambda n: bool(n.effect.slides),
    "hammer_on": lambda n: n.effect.hammer,
    "pull_off":  lambda n: n.effect.pullOff,
    "harmonic":  lambda n: n.effect.harmonic is not None,
    "tremolo":   lambda n: n.effect.tremoloPicking is not None,
    "palm_mute": lambda n: n.effect.palmMute,
}


def find_tabs(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.suffix.lower() in GP_EXTENSIONS)


def count_techniques(track) -> dict[str, int]:
    counts = {k: 0 for k in TECHNIQUE_FLAGS}
    for measure in track.measures:
        for voice in measure.voices:
            for beat in voice.beats:
                for note in beat.notes:
                    for name, check in TECHNIQUE_FLAGS.items():
                        try:
                            if check(note):
                                counts[name] += 1
                        except Exception:
                            pass
    return counts


def extract_file(path: Path) -> dict | None:
    try:
        song = guitarpro.parse(str(path))
    except Exception as exc:
        reason = "unsupported format (GP7? convert to GP5)" if "unsupported version" in str(exc) else str(exc)
        console.print(f"  [bold yellow][WARN][/] {path.name}: {reason}")
        return None

    track_details = []
    total_hits = 0
    for track in song.tracks:
        techniques = count_techniques(track)
        active = {k: v for k, v in techniques.items() if v}
        notes = sum(
            len(beat.notes)
            for m in track.measures for v in m.voices for beat in v.beats
        )
        bars = len(track.measures)
        total_hits += len(active)
        track_details.append({
            "number": track.number, "name": fix_enc(track.name) or f"Track {track.number}",
            "notes": notes, "bars": bars,
            "note_density": round(notes / bars, 2) if bars else 0.0,
            "techniques": active,
        })

    return {
        "file": str(path), "filename": path.name,
        "title": fix_enc(song.title) or "", "artist": fix_enc(song.artist) or "",
        "bpm": song.tempo, "bars": len(song.measureHeaders),
        "tracks": len(song.tracks), "total_technique_hits": total_hits,
        "track_details": track_details,
    }


def print_summary(results: list[dict]):
    table = Table(title=f"Library Scan — {len(results)} files parsed", box=box.SIMPLE_HEAD)
    for col, kw in [("Filename", {"style": "bold", "max_width": 40}),
                    ("BPM", {"justify": "right", "style": "cyan"}),
                    ("Tracks", {"justify": "right"}),
                    ("Technique hits", {"justify": "right", "style": "yellow"}),
                    ("Avg density", {"justify": "right"})]:
        table.add_column(col, **kw)
    for r in results:
        avg = round(sum(t["note_density"] for t in r["track_details"]) / len(r["track_details"]), 1) \
              if r["track_details"] else 0.0
        table.add_row(r["filename"], str(r["bpm"]), str(r["tracks"]),
                      str(r["total_technique_hits"]), str(avg))
    console.print(table)


@click.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False))
@click.option("--output", "-o", default="data/library_scan.json", show_default=True)
def main(folder, output):
    """Walk FOLDER, extract data from every Guitar Pro file, save results to JSON."""
    folder_path = Path(folder)
    tab_files = find_tabs(folder_path)
    if not tab_files:
        console.print(f"[bold red]No Guitar Pro files found in {folder}[/]")
        sys.exit(1)

    console.print(f"\n[bold]Found {len(tab_files)} tab file(s) in [cyan]{folder}[/][/]\n")
    results = [r for path in rich_track(tab_files, description="Parsing tabs...")
               if (r := extract_file(path)) is not None]

    console.print()
    print_summary(results)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2))
    console.print(f"\n[green]Full results saved to:[/] {output_path}")
    console.print(f"[dim]Parsed {len(results)}/{len(tab_files)} files successfully.[/]")


if __name__ == "__main__":
    main()
