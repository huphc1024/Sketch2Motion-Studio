import unittest

from locales import (
    CHINESE,
    ENGLISH,
    drawing_style_choices,
    get_ui_text,
    normalize_drawing_style,
    normalize_video_format,
    video_format_choices,
)


class LocaleTests(unittest.TestCase):
    def test_chinese_strings_are_available(self):
        text = get_ui_text(CHINESE)

        self.assertEqual(text["generate_video"], "生成视频")
        self.assertEqual(text["input_image"], "输入涂鸦/照片")

    def test_choice_values_do_not_change_between_languages(self):
        self.assertEqual(
            [value for _, value in drawing_style_choices(ENGLISH)],
            [value for _, value in drawing_style_choices(CHINESE)],
        )
        self.assertEqual(
            [value for _, value in video_format_choices(ENGLISH)],
            [value for _, value in video_format_choices(CHINESE)],
        )

    def test_unknown_language_defaults_to_english(self):
        self.assertEqual(get_ui_text("unknown"), get_ui_text(ENGLISH))
        self.assertEqual(get_ui_text("中文"), get_ui_text(CHINESE))

    def test_localized_choice_labels_normalize_to_stable_values(self):
        self.assertEqual(normalize_drawing_style("平滑"), "smooth")
        self.assertEqual(normalize_video_format("竖屏 9:16 (1080x1920)"), "portrait")


if __name__ == "__main__":
    unittest.main()
