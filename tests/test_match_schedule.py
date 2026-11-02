import unittest
from datetime import datetime, timezone

from match_schedule import match_cycle


ENVIRONMENT = {
    "MATCH_CYCLE_NAME": "Pilot",
    "MATCH_SIGNUP_DEADLINE": "2026-11-05T08:00:00Z",
    "MATCH_RELEASE_AT": "2026-11-07T02:00:00Z",
}


class MatchScheduleTests(unittest.TestCase):
    def test_cycle_moves_from_signup_to_lock_to_release(self):
        signup = match_cycle(datetime(2026, 11, 4, tzinfo=timezone.utc), ENVIRONMENT)
        locked = match_cycle(datetime(2026, 11, 6, tzinfo=timezone.utc), ENVIRONMENT)
        released = match_cycle(datetime(2026, 11, 8, tzinfo=timezone.utc), ENVIRONMENT)
        self.assertEqual(signup["phase"], "signup")
        self.assertEqual(locked["phase"], "locked")
        self.assertEqual(released["phase"], "released")

    def test_incomplete_configuration_stays_in_planning(self):
        cycle = match_cycle(environ={"MATCH_CYCLE_NAME": "Pilot"})
        self.assertEqual(cycle["phase"], "planning")


if __name__ == "__main__":
    unittest.main()
