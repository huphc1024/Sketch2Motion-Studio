import unittest

from models.project import migrate_project, new_project
from stores.project_store import ProjectStore


class ProjectStoreTests(unittest.TestCase):
    def test_add_duplicate_move_and_delete_scenes(self):
        project = new_project().to_dict()
        first_id = project["scenes"][0]["id"]
        project, second_id = ProjectStore.add_scene(project, first_id)
        project, duplicate_id = ProjectStore.duplicate_scene(project, first_id)
        self.assertEqual(len(project["scenes"]), 3)

        project = ProjectStore.move_scene(project, second_id, first_id)
        self.assertEqual(project["scenes"][0]["id"], second_id)

        project, selected = ProjectStore.delete_scene(project, duplicate_id)
        self.assertEqual(len(project["scenes"]), 2)
        self.assertIn(selected, [scene["id"] for scene in project["scenes"]])

    def test_script_change_marks_existing_audio_outdated(self):
        project = new_project().to_dict()
        scene_id = project["scenes"][0]["id"]
        project["scenes"][0].update({
            "script": "old",
            "audio_url": "old.wav",
            "tts_status": "ready",
        })
        project = ProjectStore.update_scene(project, scene_id, script="new")
        self.assertEqual(project["scenes"][0]["tts_status"], "outdated")

    def test_legacy_single_image_project_is_migrated(self):
        project = migrate_project({"image": "drawing.png", "svg_path": "drawing.svg", "duration": 7})
        self.assertEqual(project.schema_version, 2)
        self.assertEqual(len(project.scenes), 1)
        self.assertEqual(project.scenes[0].image, "drawing.png")
        self.assertEqual(project.scenes[0].duration, 7)

    def test_audio_duration_includes_transition(self):
        project = new_project()
        scene = project.scenes[0]
        scene.transition.duration = 0.4
        scene.apply_audio("voice.wav", 3.2, "hash")
        self.assertAlmostEqual(scene.duration, 3.6)

    def test_visual_settings_can_be_applied_to_every_scene(self):
        project = new_project().to_dict()
        first_id = project["scenes"][0]["id"]
        project, _ = ProjectStore.add_scene(project, first_id)
        for scene in project["scenes"]:
            scene["svg_path"] = "cached.svg"
            scene["preview_url"] = "cached.mp4"
            scene["script"] = "Keep this narration"
            scene["audio_url"] = "voice.wav"

        project = ProjectStore.update_all_scene_visuals(
            project, preserve_colors=True, color_count=12, animation_scale=3.4,
        )

        for scene in migrate_project(project).scenes:
            self.assertTrue(scene.preserve_colors)
            self.assertEqual(scene.color_count, 12)
            self.assertEqual(scene.animation_scale, 3.4)
            self.assertIsNone(scene.svg_path)
            self.assertIsNone(scene.preview_url)
            self.assertEqual(scene.script, "Keep this narration")
            self.assertEqual(scene.audio_url, "voice.wav")

    def test_project_supports_ten_scenes(self):
        project = new_project().to_dict()
        selected = project["scenes"][0]["id"]
        for _ in range(9):
            project, selected = ProjectStore.add_scene(project, selected)
        self.assertEqual(len(project["scenes"]), 10)
        self.assertEqual(len({scene["id"] for scene in project["scenes"]}), 10)


if __name__ == "__main__":
    unittest.main()
