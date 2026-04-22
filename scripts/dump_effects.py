#!/usr/bin/env python3
# dump_effects.py — Dump raw note/beat effect attributes for debugging technique detection.
# Usage: python scripts/dump_effects.py path/to/song.gp5 [--limit 20]

import click
import guitarpro
from rich.console import Console

console = Console()

# Fields that are structural/metadata, not technique data — skip in output
_SKIP = {"beat", "effect", "durationPercent", "realValue", "isDefault",
         "leftHandFinger", "rightHandFinger", "pickStroke", "slapEffect"}


def dump_obj(obj, label: str):
    """Print non-boring, non-default attributes on obj."""
    rows = []
    for k in dir(obj):
        if k.startswith("_") or k in _SKIP or callable(getattr(obj, k)):
            continue
        v = getattr(obj, k)
        # Skip zero-ish values
        if v is None or v is False or v == [] or v == 0:
            continue
        # Skip enum values that represent "none/off" states
        if hasattr(v, 'value') and v.value in (0, -1):
            continue
        rows.append((k, v))
    if not rows:
        return
    console.print(f"  [bold cyan]{label}[/]")
    for k, v in rows:
        console.print(f"    [yellow]{k}[/] = {v!r}")


def has_any_effect(note, beat) -> bool:
    """Use PyGuitarPro's own isDefault flags — reliable across GP3/4/5."""
    ne_interesting = not getattr(note.effect, 'isDefault', True)
    be_interesting = not getattr(beat.effect, 'isDefault', True)
    return ne_interesting or be_interesting


@click.command()
@click.argument("filepath", type=click.Path(exists=True, dir_okay=False))
@click.option("--limit", "-n", default=20, show_default=True,
              help="Max interesting notes to dump.")
@click.option("--track", "-t", default=0, show_default=True,
              help="Only show this track number (0 = all tracks).")
def main(filepath, limit, track):
    """Dump raw effect attributes from notes that have techniques set."""
    try:
        song = guitarpro.parse(filepath)
    except Exception as exc:
        console.print(f"[bold red][ERROR][/] {exc}")
        return

    console.print(f"\n[bold]File:[/] {filepath}")
    console.print(f"[bold]Song:[/] {song.artist} — {song.title}  ({song.tempo} BPM)\n")

    found = 0
    for tr in song.tracks:
        if track and tr.number != track:
            continue
        for measure in tr.measures:
            for voice in measure.voices:
                for beat in voice.beats:
                    for note in beat.notes:
                        if found >= limit:
                            console.print(f"[dim](limit {limit} reached — pass --limit N for more)[/]")
                            return
                        if not has_any_effect(note, beat):
                            continue
                        found += 1
                        console.rule(
                            f"[bold]Track {tr.number} · Bar {measure.number} "
                            f"· String {note.string} · Fret {note.value}[/]"
                        )
                        dump_obj(note, "note")
                        dump_obj(note.effect, "note.effect")
                        dump_obj(beat.effect, "beat.effect")
                        console.print()

    if found == 0:
        console.print("[bold yellow]No notes with non-default effects found.[/]")


if __name__ == "__main__":
    main()
