from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from nodes.minimax_pipeline import ordered_references
from utils.ffmpeg import assemble_final, numeric_shot_order

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT.parent))
from ComfyUI_MusicVideo.nodes.minimax_music_video import upscale_resolution


class PipelineStructureTests(unittest.TestCase):
    def test_reference_order_is_picture_order(self):
        refs = [object(), object(), object(), object()]
        ordered = ordered_references(refs)
        self.assertEqual(list(ordered), ["ref_image_0", "ref_image_1", "ref_image_2", "ref_image_3"])
        self.assertEqual(list(ordered.values()), refs)

    def test_final_assembly_uses_numeric_shot_order(self):
        files = [Path("shot_010.mp4"), Path("shot_002.mp4"), Path("shot_001.mp4")]
        self.assertEqual([path.name for path in numeric_shot_order(files)], ["shot_001.mp4", "shot_002.mp4", "shot_010.mp4"])

    @patch("utils.ffmpeg.mux_master_audio")
    @patch("utils.ffmpeg.concatenate_silent_videos")
    def test_final_assembly_muxes_untouched_master_once(self, concatenate, mux):
        shots = [Path("shot_001.mp4"), Path("shot_002.mp4")]
        master = Path("original_master.flac")
        silent = Path("silent.mp4")
        final = Path("final.mp4")
        assemble_final(shots, master, silent, final, "ffmpeg")
        concatenate.assert_called_once_with(shots, silent, "ffmpeg")
        mux.assert_called_once_with(silent, master, final, "ffmpeg")

    def test_runtime_tree_has_no_previous_architecture_dependencies(self):
        root = Path(__file__).parents[1]
        forbidden = ["l" + "tx", "ingredients", "melband", "timeline_data", "continuity"]
        runtime = list((root / "nodes").glob("*.py")) + list((root / "utils").glob("*.py")) + [root / "__init__.py"]
        for path in runtime:
            text = path.read_text(encoding="utf-8").lower()
            self.assertFalse(any(term in text for term in forbidden), path)

    def test_source_workflow_upscale_settings_are_preserved(self):
        source = (ROOT / "nodes" / "minimax_music_video.py").read_text(encoding="utf-8")
        for setting in ('upscale_method="lanczos"', 'keep_proportion="crop"', 'crop_position="center"', 'divisible_by=2', 'device="cpu"'):
            self.assertIn(setting, source)
        self.assertNotIn('cleanup("soft")', source)

    def test_upscale_resolution_follows_selected_aspect(self):
        expected = {
            "16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080),
            "4:3": (1440, 1080), "3:4": (1080, 1440), "21:9": (2520, 1080),
        }
        self.assertEqual({aspect: upscale_resolution(aspect) for aspect in expected}, expected)
