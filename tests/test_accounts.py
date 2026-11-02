import unittest
import os
from types import SimpleNamespace
from unittest.mock import patch

import app as app_module
from app import app


class MemoryCollection:
    def __init__(self):
        self.docs = {}

    @staticmethod
    def matches(document, query):
        return all(document.get(key) == value for key, value in query.items())

    def find_one(self, query, projection=None):
        document = next((doc for doc in self.docs.values() if self.matches(doc, query)), None)
        if not document:
            return None
        if projection:
            return {key: document.get(key) for key, include in projection.items() if include and key in document}
        return dict(document)

    def update_one(self, query, update, upsert=False):
        document = next((doc for doc in self.docs.values() if self.matches(doc, query)), None)
        inserted = document is None
        if inserted:
            if not upsert:
                return SimpleNamespace(modified_count=0)
            document = dict(query)
        before = dict(document)
        if inserted:
            document.update(update.get("$setOnInsert", {}))
        document.update(update.get("$set", {}))
        for key in update.get("$unset", {}):
            document.pop(key, None)
        self.docs[document["email"]] = document
        return SimpleNamespace(modified_count=int(before != document))


class AccountFlowTests(unittest.TestCase):
    def setUp(self):
        self.original_collection = app_module.coll
        app_module.coll = MemoryCollection()
        app.config.update(
            TESTING=True,
            SECRET_KEY="account-test-secret",
            MAIL_USERNAME="mailer@example.com",
            MAIL_PASSWORD="test-password",
        )
        self.client = app.test_client()

    def tearDown(self):
        app_module.coll = self.original_collection

    def test_registration_token_is_bound_one_time_and_creates_persistent_login(self):
        with patch("app.send_account_email") as send_email:
            response = self.client.post(
                "/register", data={"registerEmail": "Student@Stanford.edu"}
            )
        self.assertEqual(response.status_code, 200)
        token = send_email.call_args.args[2]

        confirmation = self.client.get(f"/confirm_email/{token}")
        self.assertEqual(confirmation.status_code, 200)
        self.assertIn(b'actionToken', confirmation.data)

        password_response = self.client.post(
            "/set_password",
            data={
                "actionToken": token,
                "setEmail": "victim@stanford.edu",
                "password": "correct horse battery staple",
            },
        )
        self.assertEqual(password_response.status_code, 200)
        student = app_module.coll.docs["student@stanford.edu"]
        self.assertTrue(app_module.is_password_hash(student["_password"]))
        self.assertNotIn("victim@stanford.edu", app_module.coll.docs)
        with self.client.session_transaction() as login_session:
            self.assertEqual(login_session["user"], "student@stanford.edu")
            self.assertTrue(login_session.permanent)

        replay = self.client.post(
            "/set_password",
            data={"actionToken": token, "password": "another long password"},
        )
        self.assertEqual(replay.status_code, 400)

    def test_unknown_forgotten_account_is_not_disclosed(self):
        response = self.client.post(
            "/forgot", data={"forgotEmail": "unknown@stanford.edu"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("If that account exists", response.get_json()["message"])

    def test_deployed_profile_route_requires_login(self):
        response = self.client.get("/music-profile")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/?next=/music-profile", response.headers["Location"])

    def test_logout_clears_session(self):
        with self.client.session_transaction() as login_session:
            login_session["user"] = "student@stanford.edu"
        response = self.client.post("/logout")
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as login_session:
            self.assertNotIn("user", login_session)

    def test_music_profile_cannot_change_after_cycle_locks(self):
        app_module.coll.docs["student@stanford.edu"] = {
            "email": "student@stanford.edu", "confirmed": True
        }
        with self.client.session_transaction() as login_session:
            login_session["user"] = "student@stanford.edu"
        environment = {
            "MATCH_CYCLE_NAME": "Pilot",
            "MATCH_SIGNUP_DEADLINE": "2020-01-01T00:00:00Z",
            "MATCH_RELEASE_AT": "2099-01-01T00:00:00Z",
        }
        with patch.dict(os.environ, environment, clear=False):
            response = self.client.post("/api/music-profile", json={})
        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()
