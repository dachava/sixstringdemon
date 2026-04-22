#!/usr/bin/env python3
# explore_tabs.py — Parse one Guitar Pro file and print everything useful.
# Usage: python scripts/explore_tabs.py path/to/song.gp5

import sys
import click
import guitarpro
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel

console = Console()


def fix_enc(s: str) -> str:
    # GP5 strings are Latin-1 bytes; some files are actually UTF-8 saved with wrong encoding.
    # Re-encoding latin-1→utf-8 recovers accented chars (e.g. Tägtgren, Synthé).
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return s


TECHNIQUE_FLAGS = {
    "bend":       lambda n: n.bend is not None and n.bend.points,
    "vibrato":    lambda n: n.effect.vibrato,
    "slide":      lambda n: bool(n.effect.slides),
    "hammer_on":  lambda n: n.effect.hammer,
    "pull_off":   lambda n: n.effect.pullOff,
    "harmonic":   lambda n: n.effect.harmonic is not None,
    "tremolo":    lambda n: n.effect.tremoloPicking is not None,
    "palm_mute":  lambda n: n.effect.palmMute,
}


def detect_techniques(track) -> dict[str, int]:
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


def count_notes(track) -> tuple[int, int]:
    total = sum(
        len(beat.notes)
        for measure in track.measures
        for voice in measure.voices
        for beat in voice.beats
    )
    return total, len(track.measures)


def detect_sections(song) -> list[dict]:
    sections, prev_tempo, prev_ts = [], song.tempo, None
    for i, hdr in enumerate(song.measureHeaders):
        ts = (hdr.timeSignature.numerator, hdr.timeSignature.denominator.value)
        # GP5 only writes tempo on headers where it changes; fall back to previous
        raw_tempo = getattr(hdr, 'tempo', None)
        tempo = raw_tempo.value if raw_tempo else prev_tempo
        if i == 0:
            sections.append({"bar": 1, "tempo": tempo, "time_sig": f"{ts[0]}/{ts[1]}", "reason": "start"})
            prev_ts, prev_tempo = ts, tempo
            continue
        reasons = []
        if tempo != prev_tempo: reasons.append(f"tempo {prev_tempo}→{tempo}")
        if ts != prev_ts:       reasons.append(f"time sig {prev_ts[0]}/{prev_ts[1]}→{ts[0]}/{ts[1]}")
        if reasons:
            sections.append({"bar": i + 1, "tempo": tempo, "time_sig": f"{ts[0]}/{ts[1]}", "reason": ", ".join(reasons)})
        prev_tempo, prev_ts = tempo, ts
    return sections


def print_header(song, filepath):
    ts = song.measureHeaders[0].timeSignature if song.measureHeaders else None
    ts_str = f"{ts.numerator}/{ts.denominator.value}" if ts else "?"
    meta = (
        f"[bold cyan]File:[/]     {filepath}\n"
        f"[bold cyan]Title:[/]    {fix_enc(song.title) or '(unknown)'}\n"
        f"[bold cyan]Artist:[/]   {fix_enc(song.artist) or '(unknown)'}\n"
        f"[bold cyan]Tempo:[/]    {song.tempo} BPM\n"
        f"[bold cyan]Time sig:[/] {ts_str}\n"
        f"[bold cyan]Bars:[/]     {len(song.measureHeaders)}  |  "
        f"[bold cyan]Tracks:[/] {len(song.tracks)}"
    )
    console.print(Panel(meta, title="[bold white]SIXSTRINGDEMON — Tab Explorer[/]", box=box.DOUBLE_EDGE))


def print_tracks(song):
    table = Table(title="Tracks", box=box.SIMPLE_HEAD, show_lines=True)
    for col, kw in [("#", {"width": 3, "style": "dim"}), ("Track", {"style": "bold"}),
                    ("Notes", {"justify": "right"}), ("Bars", {"justify": "right"}),
                    ("Density", {"justify": "right"}), ("Techniques", {"style": "yellow"})]:
        table.add_column(col, **kw)
    for track in song.tracks:
        techniques = detect_techniques(track)
        notes, bars = count_notes(track)
        active = [k.replace("_", "-") for k, v in techniques.items() if v]
        table.add_row(str(track.number), fix_enc(track.name) or f"Track {track.number}",
                      str(notes), str(bars), str(round(notes / bars, 1) if bars else 0),
                      ", ".join(active) or "[dim]none[/]")
    console.print(table)


def print_sections(sections):
    if len(sections) <= 1:
        console.print("[dim]No tempo or time signature changes detected.[/]")
        return
    table = Table(title="Section Changes", box=box.SIMPLE_HEAD)
    for col, kw in [("Bar", {"justify": "right", "style": "bold"}), ("Tempo", {"justify": "right"}),
                    ("Time Sig", {}), ("Reason", {"style": "yellow"})]:
        table.add_column(col, **kw)
    for s in sections:
        table.add_row(str(s["bar"]), str(s["tempo"]), s["time_sig"], s["reason"])
    console.print(table)


@click.command()
@click.argument("filepath", type=click.Path(exists=True, dir_okay=False))
def main(filepath):
    """Parse a Guitar Pro file and print everything we can extract."""
    try:
        song = guitarpro.parse(filepath)
    except Exception as exc:
        msg = str(exc)
        if "unsupported version" in msg:
            console.print(f"[bold red][ERROR][/] Unsupported format in {filepath}: {exc}")
            console.print("[dim]PyGuitarPro supports GP3/GP4/GP5/GPX. GP7 (.gp from Guitar Pro 7) is not supported.[/]")
            console.print("[dim]Convert to GP5 in Guitar Pro: File → Export → Guitar Pro 5[/]")
        else:
            console.print(f"[bold red][ERROR][/] Could not parse {filepath}: {exc}")
        sys.exit(1)
    print_header(song, filepath)
    console.print()
    print_tracks(song)
    console.print()
    print_sections(detect_sections(song))


if __name__ == "__main__":
    main()
