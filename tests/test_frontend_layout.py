from pathlib import Path
import unittest


class FrontendLayoutTests(unittest.TestCase):
    def test_dom_widget_tracks_node_without_resize_feedback(self):
        source = (Path(__file__).parents[1] / "web" / "minimax_music_video.js").read_text(encoding="utf-8")
        self.assertIn("width:100%;height:100%;min-width:0;min-height:0", source)
        self.assertIn("getHeight:panelHeight", source)
        self.assertIn("item.computeSize=()=>[0,-4]", source)
        self.assertNotIn("height:740px", source)
        self.assertNotIn("node.setSize", source)

    def test_all_visible_fields_use_serialized_widgets_and_restore_on_configure(self):
        source = (Path(__file__).parents[1] / "web" / "minimax_music_video.js").read_text(encoding="utf-8")
        required = [
            "master_audio", "chunk_size", "picture_1", "picture_2", "picture_3", "picture_4",
            "prompt", "aspect_ratio", "megapixels", "project_name", "global_seed", "steps",
            "model_name", "text_encoder", "video_vae", "audio_vae", "turbo_lora",
            "ffmpeg_executable", "save_shot_previews", "stitch_final_video", "shot_index", "enable_upscale",
        ]
        names_line = next(line for line in source.splitlines() if line.startswith("const names="))
        for name in required:
            self.assertIn(f'"{name}"', names_line)
        self.assertIn("originalConfigure=node.onConfigure", source)
        self.assertIn("queueMicrotask(refreshVisibleState)", source)
        self.assertIn("el.oninput=commit", source)
