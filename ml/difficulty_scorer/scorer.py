"""
scorer.py — Rule-based difficulty scoring for Guitar Pro library entries.

Input:  one entry from library_scan.json + technique tier lookup
Output: same entry with a "difficulty" block added (score 1-10 + components)

Weights:
  45% technique  — tier-weighted rate-per-bar, geometric decay across tracks
  20% bpm        — how fast you have to execute
  20% density    — notes per second on the hardest guitar track
  15% diversity  — how many distinct technique types appear
"""

import json
import math
from pathlib import Path

TECHNIQUE_ID_MAP = {
    "bend":      "bends",
    "vibrato":   "vibrato",
    "slide":     "slides",
    "hammer_on": "hammer_ons",
    "pull_off":  "pull_offs",
    "harmonic":  "pinch_harmonics",
    "tremolo":   "tremolo_picking",
    "palm_mute": "palm_muting",
}

WEIGHTS = {"technique": 0.45, "bpm": 0.20, "density": 0.20, "diversity": 0.15}

# Keywords that identify non-guitar tracks by name (case-insensitive substring match)
_NON_GUITAR = {"vocal", "voice", "bass", "drum", "synth", "piano", "organ",
               "effect", "feedback", "choir", "strings", "fx"}


def load_tiers(techniques_path: str | Path) -> dict[str, int]:
    """Return technique_id → difficulty_tier from techniques.json."""
    with open(techniques_path) as f:
        data = json.load(f)
    return {t["id"]: t["difficulty_tier"] for t in data["techniques"]}


def _percentile(arr: list, p: float) -> float:
    if not arr:
        return 0.0
    s = sorted(arr)
    return s[min(int(len(s) * p), len(s) - 1)]


def _is_non_guitar(track: dict) -> bool:
    name = track["name"].lower()
    return any(kw in name for kw in _NON_GUITAR)


def _bpm_component(bpm: int) -> float:
    """0.0 at ≤60 BPM, 1.0 at ≥240 BPM. Linear in between."""
    return max(0.0, min((bpm - 60) / 180.0, 1.0))


def _density_component(track_details: list, bpm: int, percentile: float = 1.0) -> float:
    """
    Notes-per-second on the densest guitar track at the given bar percentile.
    Requiring at least one detected technique naturally excludes drum tracks
    that share player-name-only track labels with no guitar technique markers.
    Falls back to note_density average when bar_densities is absent (old scans).
    """
    values = []
    for t in track_details:
        if _is_non_guitar(t) or not t["techniques"]:
            continue
        bar_d = t.get("bar_densities")
        notes_per_bar = _percentile(bar_d, percentile) if bar_d else t["note_density"]
        values.append(notes_per_bar * bpm / 240)
    return min(max(values) / 25.0, 1.0) if values else 0.0


def _technique_component(track_details: list, tiers: dict[str, int]) -> float:
    """
    Rate-per-bar technique score with geometric decay across tracks (factor 0.6).
    Tracks are sorted hardest-first; each additional track contributes 60% of
    the previous, so two genuine lead parts both count while a 7-track tab of
    the same riff doesn't score 7x a 1-track tab.
    Ceiling calibrated so RTL (the library's benchmark technical song) ≈ 0.89.
    """
    track_scores = []
    for track in track_details:
        if _is_non_guitar(track) or not track["techniques"]:
            continue
        bars = max(track.get("bars", 1), 1)
        score = sum(
            tiers.get(TECHNIQUE_ID_MAP.get(tech, tech), 2) * math.log(count / bars + 1)
            for tech, count in track["techniques"].items()
        )
        if score > 0:
            track_scores.append(score)
    if not track_scores:
        return 0.0
    track_scores.sort(reverse=True)
    weighted = sum(s * (0.6 ** i) for i, s in enumerate(track_scores))
    return min(weighted / 15.0, 1.0)


def _diversity_component(track_details: list) -> float:
    """Fraction of the 8 detectable technique types present on guitar tracks."""
    unique = {tech for t in track_details if not _is_non_guitar(t) for tech in t["techniques"]}
    return min(len(unique) / 8.0, 1.0)


def score_entry(entry: dict, tiers: dict[str, int]) -> dict:
    """Return entry with a 'difficulty' block: body_score, peak_score, blended score, and components."""
    td  = entry["track_details"]
    bpm = entry["bpm"]

    bpm_c       = round(_bpm_component(bpm), 3)
    technique_c = round(_technique_component(td, tiers), 3)
    diversity_c = round(_diversity_component(td), 3)
    d_body      = round(_density_component(td, bpm, percentile=0.5), 3)
    d_peak      = round(_density_component(td, bpm, percentile=0.9), 3)

    def _raw(density):
        return (WEIGHTS["technique"] * technique_c + WEIGHTS["bpm"] * bpm_c
                + WEIGHTS["density"] * density + WEIGHTS["diversity"] * diversity_c)

    body_score = round(1.0 + _raw(d_body) * 9.0, 1)
    peak_score = round(1.0 + _raw(d_peak) * 9.0, 1)
    score      = round(0.7 * body_score + 0.3 * peak_score, 1)

    return {**entry, "difficulty": {
        "score": score, "body_score": body_score, "peak_score": peak_score,
        "components": {
            "bpm": bpm_c, "density_body": d_body, "density_peak": d_peak,
            "technique": technique_c, "diversity": diversity_c,
        },
    }}


def score_library(entries: list[dict], tiers: dict[str, int]) -> list[dict]:
    """Score all entries and return sorted hardest-first."""
    return sorted([score_entry(e, tiers) for e in entries],
                  key=lambda x: x["difficulty"]["score"], reverse=True)
