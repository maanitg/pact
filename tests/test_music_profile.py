import unittest

from app import app
from music_profile import build_music_profile, timeline_overlap, weighted_overlap


SCAN_PAYLOAD = {
    "captureMode": "spotify_scan",
    "currentItems": ["Saturn — SZA", "Pink + White — Frank Ocean", "Supercut — Lorde"],
    "rewindItems": ["Someday — The Strokes", "Nights — Frank Ocean", "Ribs — Lorde"],
    "foreverArtists": ["Frank Ocean", "The Strokes", "Lorde"],
    "tasteMode": "balanced",
}


class MusicProfileUnitTests(unittest.TestCase):
    def test_spotify_scan_normalizes_and_deduplicates(self):
        payload = dict(SCAN_PAYLOAD)
        payload["currentItems"] = [
            "  Saturn — SZA  ", "saturn — sza", "Pink + White — Frank Ocean", "Supercut — Lorde"
        ]
        profile = build_music_profile(payload)
        self.assertEqual(profile["version"], 2)
        self.assertEqual(profile["capture_mode"], "spotify_scan")
        self.assertEqual(len(profile["current_items"]), 3)
        self.assertEqual(profile["forever_artists"], ["Frank Ocean", "The Strokes", "Lorde"])

    def test_spotify_scan_requires_both_time_horizons(self):
        payload = dict(SCAN_PAYLOAD)
        payload["rewindItems"] = []
        with self.assertRaisesRegex(ValueError, "both Spotify playlists"):
            build_music_profile(payload)

    def test_artist_picker_requires_a_consistent_eight_artist_stack(self):
        profile = build_music_profile(
            {
                "captureMode": "artist_picker",
                "foreverArtists": ["Frank Ocean", "Björk", "The Strokes"],
                "currentArtists": ["SZA", "Mk.gee", "Chappell Roan"],
                "wildcardArtists": ["Aphex Twin", "Cocteau Twins"],
                "tasteMode": "discovery",
            }
        )
        self.assertEqual(profile["capture_mode"], "artist_picker")
        self.assertEqual(len(profile["top_artists"]), 8)
        self.assertEqual(profile["taste_mode"], "discovery")

    def test_incomplete_artist_picker_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "exactly 3 forever"):
            build_music_profile(
                {
                    "captureMode": "artist_picker",
                    "foreverArtists": ["SZA"],
                    "currentArtists": ["Lorde"],
                    "wildcardArtists": [],
                }
            )

    def test_weighted_overlap_rewards_shared_high_rank_items(self):
        high_rank = weighted_overlap(["SZA", "Lorde"], ["SZA", "Mitski"])
        low_rank = weighted_overlap(["Lorde", "SZA"], ["Mitski", "SZA"])
        self.assertGreater(high_rank, low_rank)

    def test_weighted_overlap_is_bounded_at_one(self):
        self.assertEqual(weighted_overlap(["SZA", "Lorde"], ["SZA", "Lorde"]), 1.0)

    def test_timeline_overlap_weights_rewind_more_than_current(self):
        base = {
            "current_items": ["Current song"], "rewind_items": ["Old favorite"],
            "forever_artists": [], "current_artists": [], "wildcard_artists": [],
        }
        current_match = dict(base, rewind_items=["Different old song"])
        rewind_match = dict(base, current_items=["Different current song"])
        self.assertGreater(timeline_overlap(base, rewind_match), timeline_overlap(base, current_match))


class MusicProfileRouteTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = app.test_client()

    def test_profile_page_offers_both_low_friction_routes(self):
        response = self.client.get("/music-profile")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Scan my Spotify", response.data)
        self.assertIn(b"Build my taste stack", response.data)
        self.assertIn(b"Repeat Rewind", response.data)
        self.assertIn(b"Choose 2 phone or computer screenshots", response.data)
        self.assertIn(b"MOBILE OR DESKTOP", response.data)
        self.assertIn(b"current-editor", response.data)
        self.assertIn(b"spotify-ocr.js", response.data)

    def test_confirmed_timeline_is_saved_and_receipt_is_rendered(self):
        response = self.client.post("/api/music-profile", json=SCAN_PAYLOAD)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["redirectUrl"], "/receipts")

        receipt = self.client.get("/receipts")
        self.assertEqual(receipt.status_code, 200)
        self.assertIn(b"ON REPEAT", receipt.data)
        self.assertIn(b"REPEAT REWIND", receipt.data)
        self.assertIn(b"Saturn", receipt.data)

    def test_artist_picker_receipt_labels_the_full_stack(self):
        response = self.client.post(
            "/api/music-profile",
            json={
                "captureMode": "artist_picker",
                "foreverArtists": ["Frank Ocean", "Björk", "The Strokes"],
                "currentArtists": ["SZA", "Mk.gee", "Chappell Roan"],
                "wildcardArtists": ["Aphex Twin", "Cocteau Twins"],
                "tasteMode": "discovery",
            },
        )
        self.assertEqual(response.status_code, 200)
        receipt = self.client.get("/receipts")
        self.assertIn(b"ARTIST STACK", receipt.data)
        self.assertIn(b"Cocteau Twins", receipt.data)

    def test_empty_profile_is_rejected(self):
        response = self.client.post("/api/music-profile", json={"captureMode": "spotify_scan"})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
