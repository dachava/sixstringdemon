"""
scorer.py — Rule-based difficulty scoring for Guitar Pro library entries.

Input:  one entry from library_scan.json + technique tier lookup
Output: same entry with a "difficulty" block added (score 1-10 + components)

Weights:
  45% technique  — what skills the song demands (tier-weighted, log-diminishing)
  20% bpm        — how fast you have to execute
  20% density    — how many notes per bar on the hardest guitar track
  15% diversity  — how many distinct technique types appear
"""

import json
import math
from pathlib import Path

# Maps our 8 detected technique names → techniques.json IDs
TECHNIQUE_ID_MAP = {
    "bend":      "bends",
    "vibrato":   "vibrato",
    "slide":     "slides",
    "hammer_on": "hammer_ons",
    "pull_off":  "pull_offs",
    "harmonic":  "pinch_harmonics",   # conservative — could be natural (lower)
    "tremolo":   "tremolo_picking",
    "palm_mute": "palm_muting",
}

WEIGHTS = {"technique": 0.45, "bpm": 0.20, "density": 0.20, "diversity": 0.15}


def load_tiers(techniques_path: str | Path) -> dict[str, int]:
    """Return technique_id → difficulty_tier from techniques.json."""
    with open(techniques_path) as f:
        data = json.load(f)
    return {t["id"]: t["difficulty_tier"] for t in data["techniques"]}


def _bpm_component(bpm: int) -> float:
    """0.0 at ≤60 BPM, 1.0 at ≥240 BPM. Linear in between."""
    return max(0.0, min((bpm - 60) / 180.0, 1.0))


def _density_component(track_details: list) -> float:
    """Max note density across tracks that have any technique — excludes pure drums."""
    densities = [t["note_density"] for t in track_details if t["techniques"]]
    return min(max(densities) / 25.0, 1.0) if densities else 0.0


def _technique_component(track_details: list, tiers: dict[str, int]) -> float:
    """
    For each technique occurrence: add tier × log(count+1).
    Log gives diminishing returns so 500 palm mutes doesn't dwarf one tapping note.
    Normalised against 150 — a song with heavy tier-5 technique density
    across multiple tracks approaches 1.0, but most songs spread out below it.
    """
    total = 0.0
    for track in track_details:
        for tech, count in track["techniques"].items():
            tier = tiers.get(TECHNIQUE_ID_MAP.get(tech, tech), 2)
            total += tier * math.log(count + 1)
    return min(total / 150.0, 1.0)


def _diversity_component(track_details: list) -> float:
    """Fraction of the 8 detectable technique types present anywhere in the song."""
    unique = {tech for t in track_details for tech in t["techniques"]}
    return min(len(unique) / 8.0, 1.0)


def score_entry(entry: dict, tiers: dict[str, int]) -> dict:
    """Return entry with a 'difficulty' block containing score (1-10) and components."""
    td = entry["track_details"]
    components = {
        "bpm":       round(_bpm_component(entry["bpm"]), 3),
        "density":   round(_density_component(td), 3),
        "technique": round(_technique_component(td, tiers), 3),
        "diversity": round(_diversity_component(td), 3),
    }
    raw = sum(WEIGHTS[k] * v for k, v in components.items())
    return {**entry, "difficulty": {"score": round(1.0 + raw * 9.0, 1), "components": components}}


def score_library(entries: list[dict], tiers: dict[str, int]) -> list[dict]:
    """Score all entries and return sorted hardest-first."""
    return sorted([score_entry(e, tiers) for e in entries],
                  key=lambda x: x["difficulty"]["score"], reverse=True)
