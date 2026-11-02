import os
from datetime import datetime, timezone


def parse_utc(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def match_cycle(now=None, environ=None):
    """Return the public state of the configured batch-matching cycle."""
    environ = environ or os.environ
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    deadline = parse_utc(environ.get("MATCH_SIGNUP_DEADLINE"))
    release_at = parse_utc(environ.get("MATCH_RELEASE_AT"))
    name = environ.get("MATCH_CYCLE_NAME", "Next Wavelength drop")

    if not deadline or not release_at or release_at <= deadline:
        return {
            "name": name,
            "phase": "planning",
            "message": "The next matching window has not been announced yet.",
            "deadline": deadline,
            "release_at": release_at,
        }
    if now < deadline:
        phase = "signup"
        message = "Your profile stays editable until signups close."
    elif now < release_at:
        phase = "locked"
        message = "Profiles are locked while the cohort is matched and reviewed."
    else:
        phase = "released"
        message = "This cohort's results have been released."
    return {
        "name": name,
        "phase": phase,
        "message": message,
        "deadline": deadline,
        "release_at": release_at,
    }
