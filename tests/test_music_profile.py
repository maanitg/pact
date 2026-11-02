import unittest

from app import app
from music_profile import build_music_profile, weighted_overlap


class MusicProfileUnitTests(unittest.TestCase):
    def test_profile_normalizes_deduplicates_and_limits_input(self):
        profile = build_music_profile(
            {
                "topArtists": ["  Frank Ocean  ", "frank ocean", "SZA"],
                "topTracks": ["Pink + White — Frank Ocean"],
                "coreArtists": ["The Strokes", "The Strokes"],
                "tasteMode": "discovery",
            }
        )
        self.assertEqual(profile["top_artists"], ["Frank Ocean", "SZA"])
        self.assertEqual(profile["core_artists"], ["The Strokes"])
        self.assertEqual(profile["taste_mode"], "discovery")

    def test_profile_requires_music(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            build_music_profile({"topArtists": [], "topTracks": []})

    def test_weighted_overlap_rewards_shared_high_rank_items(self):
        high_rank = weighted_overlap(["SZA", "Lorde"], ["SZA", "Mitski"])
        low_rank = weighted_overlap(["Lorde", "SZA"], ["Mitski", "SZA"])
        self.assertGreater(high_rank, low_rank)


class MusicProfileRouteTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = app.test_client()

    def test_profile_page_is_available_without_spotify_oauth(self):
        response = self.client.get("/music-profile")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"SCAN YOUR TASTE", response.data)

    def test_confirmed_text_is_saved_and_receipt_is_rendered(self):
        response = self.client.post(
            "/api/music-profile",
            json={
                "topArtists": ["SZA", "Lorde"],
                "topTracks": ["Saturn — SZA"],
                "coreArtists": ["Frank Ocean"],
                "tasteMode": "balanced",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["redirectUrl"], "/receipts")

        receipt = self.client.get("/receipts")
        self.assertEqual(receipt.status_code, 200)
        self.assertIn(b"SZA", receipt.data)
        self.assertIn(b"SONIC FINGERPRINT", receipt.data)

    def test_empty_profile_is_rejected(self):
        response = self.client.post(
            "/api/music-profile", json={"topArtists": [], "topTracks": []}
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
