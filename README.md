# Wavelength / Spotify Marriage Pact

An MVP for matching Stanford participants through their music taste without
requiring Spotify Web API approval.

## MVP participant journey

1. Complete the existing friend/partner questionnaire.
2. Open Spotify's mobile **Listening stats** screen.
3. Upload screenshots of Top artists and Top songs.
4. The browser runs OCR locally with Tesseract.js. Screenshot pixels are not
   posted to Flask.
5. Correct the extracted names, add up to three enduring artists, and choose a
   matching preference.
6. Save the confirmed profile and view a personalized receipt.

The profile endpoint works in a local demo session without MongoDB. When a
logged-in participant and `MONGO_URI` are present, the same confirmed profile is
stored on their user record.

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

Set the variables from `.env.example` through your deployment environment. The
app intentionally contains no production credentials.

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Current MVP boundary

The pull request covers music-profile capture, correction, persistence, and the
receipt. A production batch matcher, screenshot-layout-specific OCR tuning, data
export ingestion, and locally bundled OCR assets are follow-up work.
