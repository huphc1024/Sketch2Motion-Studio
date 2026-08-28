import unittest

from models.project import new_project, new_scene
from services.timeline import build_master_timeline


class TimelineTests(unittest.TestCase):
    def test_master_timeline_uses_scene_durations_as_source_of_truth(self):
        project = new_project()
        project.scenes[0].duration = 3.0
        project.scenes[0].audio_url = "voice-1.wav"
        project.scenes[0].audio_duration = 2.0
        second = new_scene(1)
        second.duration = 4.0
        project.scenes.append(second)

        timeline = build_master_timeline(project.to_dict())
        self.assertEqual((timeline[0].start, timeline[0].end), (0.0, 3.0))
        self.assertEqual((timeline[1].start, timeline[1].end), (3.0, 7.0))
        self.assertAlmostEqual(timeline[0].voice_start, 0.15)
        self.assertAlmostEqual(timeline[0].voice_end, 2.15)

    def test_no_voice_mode_has_no_audio_timestamps(self):
        project = new_project()
        project.voice_settings.language = "none"
        project.scenes[0].audio_url = "stale.wav"
        timeline = build_master_timeline(project.to_dict())
        self.assertIsNone(timeline[0].voice_start)


if __name__ == "__main__":
    unittest.main()
