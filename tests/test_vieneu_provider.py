import unittest
from unittest.mock import patch

from services.tts.providers.vieneu import VieNeuProvider


class VieNeuProviderTests(unittest.TestCase):
    def test_offline_fallback_contains_all_v3_turbo_voices(self):
        provider = VieNeuProvider(base_url="http://127.0.0.1:1", timeout=0.01)
        with patch.object(provider, "_request_json", side_effect=RuntimeError("offline")), patch.dict(
            "os.environ", {"VIENEU_TTS_VOICES": ""}, clear=False
        ):
            voices = provider.get_voices()
        self.assertEqual(len(voices), 20)
        self.assertIn("Phạm Tuyên", {voice.id for voice in voices})
        self.assertIn("Kim Thanh", {voice.id for voice in voices})

    def test_parser_deduplicates_voice_ids(self):
        voices = VieNeuProvider._parse_voices([
            {"id": "Adam", "name": "Adam"},
            ("Adam duplicate", "Adam"),
            "Xuân Vĩnh",
        ])
        self.assertEqual([voice.id for voice in voices], ["Adam", "Xuân Vĩnh"])


if __name__ == "__main__":
    unittest.main()
