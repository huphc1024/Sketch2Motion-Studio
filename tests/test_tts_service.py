import io
import tempfile
import unittest
import wave
from pathlib import Path

from services.tts.base import TTSProvider
from services.tts.service import TTSService
from services.tts.types import ProviderAudio, SynthesisInput, TTSVoice


class FakeProvider(TTSProvider):
    id = "fake"
    name = "Fake"
    supported_languages = ("vi",)

    def __init__(self):
        self.calls = 0

    def get_voices(self):
        return [TTSVoice("voice", "Voice", "vi")]

    def synthesize(self, input):
        self.calls += 1
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(8000)
            stream.writeframes(b"\x00\x00" * 4000)
        return ProviderAudio(buffer.getvalue())


class TTSServiceTests(unittest.TestCase):
    def test_hash_cache_prevents_duplicate_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            service = TTSService(Path(directory))
            provider = FakeProvider()
            service.register(provider)
            request = SynthesisInput("Xin chào", "voice", "vi")
            first = service.synthesize("fake", request)
            second = service.synthesize("fake", request)
            self.assertEqual(provider.calls, 1)
            self.assertFalse(first.cached)
            self.assertTrue(second.cached)
            self.assertAlmostEqual(second.duration, 0.5)

    def test_language_support_is_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            service = TTSService(Path(directory))
            service.register(FakeProvider())
            with self.assertRaises(ValueError):
                service.synthesize("fake", SynthesisInput("Hello", "voice", "en"))


if __name__ == "__main__":
    unittest.main()
