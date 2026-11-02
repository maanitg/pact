import re
from datetime import datetime, timezone


MAX_ITEMS = 20
VALID_TASTE_MODES = {"similar", "balanced", "discovery"}
VALID_CAPTURE_MODES = {"spotify_scan", "artist_picker"}


def normalize_item(value):
    value = re.sub(r"\s+", " ", str(value or "")).strip(" \t\r\n-–—•·,")
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
    capture_mode = normalize_item(payload.get("captureMode", "spotify_scan")).lower()
    if capture_mode not in VALID_CAPTURE_MODES:
        capture_mode = "spotify_scan"

    current_items = normalize_items(payload.get("currentItems") or payload.get("topTracks"))
    rewind_items = normalize_items(payload.get("rewindItems"))
    forever_artists = normalize_items(
        payload.get("foreverArtists") or payload.get("coreArtists"), limit=3
    )
    current_artists = normalize_items(payload.get("currentArtists"), limit=3)
    wildcard_artists = normalize_items(payload.get("wildcardArtists"), limit=2)
    legacy_artists = normalize_items(payload.get("topArtists"))
    taste_mode = normalize_item(payload.get("tasteMode", "balanced")).lower()
    if taste_mode not in VALID_TASTE_MODES:
        taste_mode = "balanced"

    if capture_mode == "spotify_scan":
        if len(current_items) < 3 or len(rewind_items) < 3:
            raise ValueError("Keep at least 3 items from both Spotify playlists.")
        if len(forever_artists) != 3:
            raise ValueError("Add exactly 3 forever artists.")
    elif len(forever_artists) != 3 or len(current_artists) != 3 or len(wildcard_artists) != 2:
        raise ValueError("Choose exactly 3 forever, 3 current, and 2 wildcard artists.")

    artist_stack = normalize_items(
        forever_artists + current_artists + wildcard_artists + legacy_artists, limit=8
    )
    return {
        "version": 2,
        "source": capture_mode,
        "capture_mode": capture_mode,
        "coverage": "current_rotation_plus_repeat_rewind_and_identity_anchors",
        "current_items": current_items,
        "rewind_items": rewind_items,
        "forever_artists": forever_artists,
        "current_artists": current_artists,
        "wildcard_artists": wildcard_artists,
        # Compatibility fields used by the receipt and legacy matching script.
        "top_artists": artist_stack,
        "top_tracks": current_items,
        "core_artists": forever_artists,
        "taste_mode": taste_mode,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def weighted_overlap(left, right):
    """Return a rank-aware overlap score for one music signal."""
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
    return round(shared_weight / total_weight, 4) if total_weight else 0.0


def timeline_overlap(left_profile, right_profile):
    """Combine current, enduring, and identity overlap for a future matcher."""
    current = weighted_overlap(
        left_profile.get("current_items", []), right_profile.get("current_items", [])
    )
    rewind = weighted_overlap(
        left_profile.get("rewind_items", []), right_profile.get("rewind_items", [])
    )
    left_artists = normalize_items(
        left_profile.get("forever_artists", [])
        + left_profile.get("current_artists", [])
        + left_profile.get("wildcard_artists", []),
        limit=8,
    )
    right_artists = normalize_items(
        right_profile.get("forever_artists", [])
        + right_profile.get("current_artists", [])
        + right_profile.get("wildcard_artists", []),
        limit=8,
    )
    identity = weighted_overlap(left_artists, right_artists)
    return round((0.35 * current) + (0.40 * rewind) + (0.25 * identity), 4)
