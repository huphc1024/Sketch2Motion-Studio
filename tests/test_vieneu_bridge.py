import unittest

from fastapi.testclient import TestClient

from services.tts.vieneu_bridge import _normalize_voices, app


class VieNeuBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_does_not_eagerly_load_model(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["modelLoaded"])

    def test_bridge_rejects_non_vietnamese_before_model_load(self):
        response = self.client.post("/synthesize", json={"text": "Hello", "language": "en"})
        self.assertEqual(response.status_code, 400)

    def test_health_advertises_full_v3_catalog(self):
        response = self.client.get("/health")
        self.assertEqual(response.json()["builtInVoiceCount"], 20)

    def test_voice_normalization_keeps_every_unique_sdk_voice(self):
        voices = _normalize_voices([
            ("Giọng Bắc", "Bac"),
            {"id": "Nam", "description": "Giọng Nam"},
            "Custom",
            ("Trùng", "Bac"),
        ])
        self.assertEqual([voice["id"] for voice in voices], ["Bac", "Nam", "Custom"])


if __name__ == "__main__":
    unittest.main()
