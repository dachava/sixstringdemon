# SIXSTRINGDEMON — Claude Context

## What this project is
Personal metal guitar learning engine. Ingests Guitar Pro tab files, extracts technique and difficulty data, eventually scores songs, predicts practice progress, and surfaces the next technique to learn.

**Stack:** Python, Bash, Terraform (future), Markdown notes. No AWS yet.

## Current state: Phase 0 complete, Phase 1 next

### Phase 0 — done
- Project scaffold at `/home/chava/Source/dev/sixstringdemon/`
- `scripts/bootstrap.sh` — venv setup, dependency install, sanity checks
- `scripts/explore_tabs.py` — single-file CLI parser (click + rich)
- `scripts/explore_library.py` — recursive folder scanner, saves `data/library_scan.json`
- `scripts/dump_effects.py` — diagnostic tool for inspecting raw PyGuitarPro effect attributes
- `data/techniques.json` — 16-technique reference, difficulty tiers 1–8, dependencies, BPM relevance

### Phase 1 — next
Rule-based difficulty scorer in `ml/difficulty_scorer/`. Input: `library_scan.json` entry. Output: score 1–10. Weight BPM, note density, technique diversity, and high-tier techniques from `techniques.json`. Rule-based first (no labeled training data yet); corrections become training set later.

## Rules — always follow these
- Python only, no AWS until explicitly started
- `click` for CLI args, `rich` for all terminal output — no bare `print()`
- Scripts in `scripts/` must stay under 150 lines — split helpers into functions or a shared lib module
- Errors warn and skip, never crash
- No comments unless the WHY is non-obvious

## Key technical facts learned from real data
- Technique fields all live on `note.effect`, not `note` directly
- `bend` → `note.effect.bend` (BendEffect object, check `.points`)
- `vibrato` → `note.effect.vibrato` (bool)
- `hammer_on` → `note.effect.hammer` (bool)
- `pull_off` → `note.effect.pullOff` (bool)
- `slide` → `note.effect.slides` (list of SlideType)
- `palm_mute` → `note.effect.palmMute` (bool)
- `harmonic` → `note.effect.harmonic` (object or None)
- GP5 `MeasureHeader` only has `.tempo` on bars where tempo changes — use `getattr(hdr, 'tempo', None)`
- GP5/GP4 string encoding: re-encode latin-1 → utf-8 to recover accented chars (`fix_enc` helper in both explorer scripts)
- GP7 (`.gp` from Guitar Pro 7) is not supported by PyGuitarPro — it's a ZIP container, shows as version `'KC'`
- `total_technique_hits` in library_scan.json = distinct technique types per track, summed across tracks (diversity score, not volume)

## Formats supported
GP3, GP4, GP5, GPX. GP7 (`.gp`) not supported — user must export to GP5.

## Git
- `docs/` is gitignored (local only)
- `data/library_scan.json` is gitignored (generated)
- `.venv/` is gitignored
