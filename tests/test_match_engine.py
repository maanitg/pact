import unittest

from app import app
from match_engine import maximum_weight_pairs, mutual_relationship, score_breakdown
from match_lab import SAMPLE_COHORT, build_match_lab


class MatchEngineTests(unittest.TestCase):
    def test_score_breakdown_is_bounded_and_explainable(self):
        left = SAMPLE_COHORT[0]["profile"]
        right = SAMPLE_COHORT[1]["profile"]
        breakdown = score_breakdown(left, right)
        self.assertGreater(breakdown["total"], 0)
        self.assertLessEqual(breakdown["total"], 1)
        self.assertIn("Nights — Frank Ocean", breakdown["shared_rewind"])
        self.assertIn("SZA", breakdown["shared_artists"])

    def test_mutual_partner_eligibility_requires_both_preferences(self):
        gray, hayden = SAMPLE_COHORT[6], SAMPLE_COHORT[7]
        self.assertEqual(mutual_relationship(gray, hayden), "Partner")
        incompatible = dict(hayden, attracted_to=["Woman"])
        self.assertIsNone(mutual_relationship(gray, incompatible))

    def test_maximum_weight_matching_recovers_known_pairs(self):
        result = maximum_weight_pairs(SAMPLE_COHORT, respect_constraints=True)
        self.assertEqual(len(result["pairs"]), 4)
        self.assertTrue(all(pair["expected"] for pair in result["pairs"]))
        self.assertFalse(result["unmatched"])

    def test_expected_pairs_survive_twenty_percent_noise(self):
        lab = build_match_lab(20, True)
        self.assertEqual(lab["metrics"]["expected_recovered"], 4)


class MatchLabRouteTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = app.test_client()

    def test_match_lab_renders_without_a_database(self):
        response = self.client.get("/match-lab?noise=20&constraints=1")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"MATCH LAB", response.data)
        self.assertIn(b"4/4", response.data)
        self.assertIn(b"Compatibility matrix", response.data)

    def test_match_lab_api_returns_pairs_and_explanations(self):
        response = self.client.get("/api/match-lab?noise=0&constraints=1")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data["pairs"]), 4)
        self.assertIn("shared_rewind", data["pairs"][0]["breakdown"])


if __name__ == "__main__":
    unittest.main()
