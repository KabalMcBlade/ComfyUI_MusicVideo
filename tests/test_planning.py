import math
import unittest

from nodes.planning import h3_generation_frames, plan_shots, shots_to_render, trim_frame_count


class PlanningTests(unittest.TestCase):
    def test_chunk_planning_uses_exact_final_duration(self):
        shots = plan_shots(19.08, 5.0)
        self.assertEqual([(shot.start, shot.end) for shot in shots], [(0.0, 5.0), (5.0, 10.0), (10.0, 15.0), (15.0, 19.08)])
        for actual, expected in zip([shot.duration for shot in shots], [5.0, 5.0, 5.0, 4.08]):
            self.assertTrue(math.isclose(actual, expected))

    def test_h3_lengths_and_trim_counts(self):
        self.assertEqual(h3_generation_frames(5.0), 124)
        self.assertEqual(h3_generation_frames(4.08), 107)
        self.assertEqual([trim_frame_count(value) for value in (5.0, 5.0, 5.0, 4.08)], [120, 120, 120, 98])

    def test_invalid_planning_inputs_fail(self):
        for duration, chunk in ((0, 5), (5, 0), (float("nan"), 5)):
            with self.subTest(duration=duration, chunk=chunk), self.assertRaises(ValueError):
                plan_shots(duration, chunk)

    def test_shot_selection_uses_displayed_one_based_index(self):
        shots = plan_shots(15, 5)
        self.assertEqual(shots_to_render(shots, -1), shots)
        self.assertEqual([shot.index for shot in shots_to_render(shots, 2)], [2])
        for index in (0, 4):
            with self.assertRaisesRegex(ValueError, "between 1 and 3"):
                shots_to_render(shots, index)
