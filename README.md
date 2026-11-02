# Wavelength / Spotify Marriage Pact

An MVP for matching Stanford participants through their music taste without
requiring Spotify Web API approval.

## MVP participant journeys

Participants choose one of two consistent routes:

1. **Scan my Spotify:** upload exactly two On Repeat and two Repeat Rewind
   screenshots, let the browser run OCR locally, correct each extracted item in
   a numbered mobile-friendly editor, and add three forever artists.
2. **Build my taste stack:** choose exactly three forever artists, three current
   artists, and two wildcard artists without uploading anything.

Both routes end with a matching preference and personalized receipt. Screenshot
pixels are never posted to Flask; only confirmed text is saved.

## Synthetic Match Lab

Open `/match-lab` to exercise the scoring and cohort optimizer without touching
MongoDB or using real participants. The lab includes eight fictional profiles,
known expected pairs, mutual friend/partner eligibility, a complete score matrix,
per-pair explanations, and deterministic 0–50% noise tests. The optimizer uses
maximum-weight general-graph matching rather than the legacy matching script.

The profile endpoint works in a local demo session without MongoDB. When a
logged-in participant and `MONGO_URI` are present, the same confirmed profile is
stored on their user record.

## Local setup

```powershell
python -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
$env:SECRET_KEY = & ".\.venv\Scripts\python.exe" -c "import secrets; print(secrets.token_urlsafe(48))"
$env:SESSION_COOKIE_SECURE = "false"
& ".\.venv\Scripts\python.exe" app.py
```

No MongoDB or mail configuration is required for the local profile demo. Set
real values from `.env.example` through the production deployment environment;
do not copy its placeholders unchanged. The app intentionally contains no
production credentials.

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Current MVP boundary

The pull request covers two-lane music-profile capture, correction, persistence,
timeline-weighted scoring primitives, and the receipt. A production batch
matcher, screenshot-layout-specific OCR tuning, data-export ingestion, and
locally bundled OCR assets are follow-up work.
