# gp7.py — Parser for Guitar Pro 7/8 (.gp) files.
# GP7+ files are ZIP archives containing GPIF XML — not readable by PyGuitarPro.
# Returns the same dict schema as explore_library.extract_file.

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

# Technique name → (property names that trigger it, child tags that trigger it)
TECHNIQUE_MAP = {
    "bend":      ({"Bended"},                   set()),
    "vibrato":   (set(),                        {"Vibrato"}),
    "slide":     ({"Slide"},                    set()),
    "hammer_on": ({"HopoOrigin"},               set()),
    "pull_off":  ({"HopoDestination"},          set()),
    "harmonic":  ({"Harmonic", "HarmonicType"}, set()),
    "palm_mute": ({"PalmMuted"},                set()),
    "tapping":   ({"Tapped"},                   set()),
}


def _tempo(root) -> int:
    """BPM from MasterTrack automations. Value format: 'BPM beats'."""
    for auto in root.findall('.//MasterTrack/Automations/Automation'):
        if auto.findtext('Type') == 'Tempo':
            return int(float(auto.findtext('Value', '120').split()[0]))
    return 120


def _index(root, tag: str) -> dict:
    """Build id → element lookup for a given tag across the whole document."""
    return {el.get('id'): el for el in root.iter(tag)}


def _ids(el, child_tag: str) -> list[str]:
    """Return space-separated IDs from a child element, dropping sentinel -1."""
    return [x for x in (el.findtext(child_tag) or '').split() if x != '-1']


def _techniques(note_el) -> set[str]:
    """Return set of technique names present on a single Note element."""
    props    = {p.get('name') for p in note_el.findall('Properties/Property')}
    children = {c.tag for c in note_el if c.tag != 'Properties'}
    return {
        tech for tech, (prop_set, child_set) in TECHNIQUE_MAP.items()
        if (prop_set & props) or (child_set & children)
    }


def parse(path: Path) -> dict | None:
    """Parse a .gp file and return a library_scan-compatible dict, or None on failure."""
    try:
        with zipfile.ZipFile(path) as z:
            root = ET.fromstring(z.read('Content/score.gpif').decode('utf-8'))
    except Exception:
        return None

    title  = (root.findtext('Score/Title')  or '').strip()
    artist = (root.findtext('Score/Artist') or '').strip()
    tempo  = _tempo(root)
    total_bars = len(root.findall('.//MasterBars/MasterBar'))

    bars_idx   = _index(root, 'Bar')
    voices_idx = _index(root, 'Voice')
    beats_idx  = _index(root, 'Beat')
    notes_idx  = _index(root, 'Note')

    # Bar IDs are in MasterBar/Bars — one ID per track per master bar, in track order.
    # Build track_index → [bar_id, ...] by reading each MasterBar in sequence.
    track_els = root.findall('.//Tracks/Track')
    num_tracks = len(track_els)
    track_bar_ids: list[list[str]] = [[] for _ in range(num_tracks)]
    for mb in root.findall('.//MasterBars/MasterBar'):
        for i, bar_id in enumerate((mb.findtext('Bars') or '').split()):
            if i < num_tracks and bar_id != '-1':
                track_bar_ids[i].append(bar_id)

    track_details = []
    total_hits = 0

    for idx, track_el in enumerate(track_els):
        track_id = track_el.get('id', str(idx))
        name = (track_el.findtext('Name') or f'Track {track_id}').strip()
        bar_ids = track_bar_ids[idx]

        note_count = 0
        tech_counts = {k: 0 for k in TECHNIQUE_MAP}

        for bar_id in bar_ids:
            bar_el = bars_idx.get(bar_id)
            if bar_el is None:
                continue
            for voice_id in _ids(bar_el, 'Voices'):
                voice_el = voices_idx.get(voice_id)
                if voice_el is None:
                    continue
                for beat_id in _ids(voice_el, 'Beats'):
                    beat_el = beats_idx.get(beat_id)
                    if beat_el is None:
                        continue
                    note_ids = _ids(beat_el, 'Notes')
                    note_count += len(note_ids)
                    for note_id in note_ids:
                        note_el = notes_idx.get(note_id)
                        if note_el is not None:
                            for tech in _techniques(note_el):
                                tech_counts[tech] += 1

        bars_count = len(bar_ids)
        active = {k: v for k, v in tech_counts.items() if v}
        total_hits += len(active)
        track_details.append({
            'number':       int(track_id) + 1,
            'name':         name,
            'notes':        note_count,
            'bars':         bars_count,
            'note_density': round(note_count / bars_count, 2) if bars_count else 0.0,
            'techniques':   active,
        })

    return {
        'file':                 str(path),
        'filename':             path.name,
        'title':                title,
        'artist':               artist,
        'bpm':                  tempo,
        'bars':                 total_bars,
        'tracks':               len(track_details),
        'total_technique_hits': total_hits,
        'track_details':        track_details,
    }
