# Wavelength / Spotify Marriage Pact

An MVP for matching Stanford participants through their music taste without
requiring Spotify Web API approval.

## MVP participant journeys

Participants choose one of two consistent routes:

1. **Scan my Spotify:** upload exactly two On Repeat and two Repeat Rewind
   screenshots. The browser crops away Spotify chrome, upscales the list, pairs
   title/artist lines using OCR bounding boxes, and flags unpaired rows for
   correction in a numbered mobile-friendly editor.
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

## Accounts and matching cycles

Deployed mode uses persistent MongoDB accounts. Registration verifies a
`@stanford.edu` mailbox, and registration/reset links are purpose-bound,
one-time actions that expire after one hour. Passwords are hashed and login
sessions last 30 days by default. The database-free local demo remains available
for testing the intake flow.

Matching is designed as a cohort batch, not a continuously changing feed:

1. Participants can edit their profile until `MATCH_SIGNUP_DEADLINE`.
2. The cohort locks; an idempotent background job enriches profiles, builds the
   compatibility graph, and computes one maximum-weight pairing set.
3. An admin reviews unmatched participants and low-confidence pairs.
4. Results become visible together at `MATCH_RELEASE_AT` and remain immutable
   for that cycle. Late participants enter the next cycle.

Do not run matching from a Flask request or an in-process timer. Production
should invoke a separate, retry-safe batch command from the hosting platform's
scheduler and store the cycle name with every result. The current PR displays
the configured cycle state; the production semantic enrichment and batch
command remain follow-up work.

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
node tests/spotify_ocr.test.js
```

## Current MVP boundary

The pull request covers two-lane music-profile capture, correction, persistence,
timeline-weighted scoring primitives, and the receipt. A production batch
matcher, screenshot-layout-specific OCR tuning, data-export ingestion, and
locally bundled OCR assets are follow-up work.
