import re
from datetime import datetime, timezone


MAX_ITEMS = 20
VALID_TASTE_MODES = {"similar", "balanced", "discovery"}


def normalize_item(value):
    value = re.sub(r"\s+", " ", str(value or "")).strip(" \t\r\n-–—•·")
    return value[:120]


def normalize_items(values, limit=MAX_ITEMS):
    if not isinstance(values, list):
        return []

    result = []
    seen = set()
    for value in values:
        cleaned = normalize_item(value)
        key = cleaned.casefold()
        if len(cleaned) < 2 or key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
        if len(result) >= limit:
            break
    return result


def build_music_profile(payload):
    top_artists = normalize_items(payload.get("topArtists"))
    top_tracks = normalize_items(payload.get("topTracks"))
    core_artists = normalize_items(payload.get("coreArtists"), limit=5)
    taste_mode = normalize_item(payload.get("tasteMode", "balanced")).lower()

    if not top_artists and not top_tracks:
        raise ValueError("Add at least one artist or track before creating your profile.")
    if taste_mode not in VALID_TASTE_MODES:
        taste_mode = "balanced"

    return {
        "version": 1,
        "source": "spotify_listening_stats_screenshot",
        "coverage": "approximately_last_4_weeks",
        "top_artists": top_artists,
        "top_tracks": top_tracks,
        "core_artists": core_artists,
        "taste_mode": taste_mode,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def weighted_overlap(left, right):
    """Return a rank-aware overlap score for the future matching job."""

    left_index = {item.casefold(): index for index, item in enumerate(left)}
    right_index = {item.casefold(): index for index, item in enumerate(right)}
    shared = set(left_index) & set(right_index)
    if not shared:
        return 0.0

    shared_weight = sum(
        1 / (1 + left_index[item]) + 1 / (1 + right_index[item]) for item in shared
    )
    total_weight = sum(1 / (1 + index) for index in range(len(left))) + sum(
        1 / (1 + index) for index in range(len(right))
    )
    return round((2 * shared_weight) / total_weight, 4) if total_weight else 0.0
