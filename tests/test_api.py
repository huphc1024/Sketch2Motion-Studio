import unittest

from fastapi.testclient import TestClient

from app import app


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_lists_tts_providers(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertIn("vieneu", response.json()["ttsProviders"])

    def test_vieneu_does_not_claim_english_support(self):
        response = self.client.post("/api/tts/generate", json={
            "provider": "vieneu",
            "text": "Hello",
            "language": "en",
            "voiceId": "default",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("does not support", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
