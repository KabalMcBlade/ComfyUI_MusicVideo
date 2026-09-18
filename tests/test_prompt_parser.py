# Copyright (C) 2026 Michele Condo'
# This file is part of ComfyUI MiniMax H3 Music Video.
# SPDX-License-Identifier: GPL-3.0-only

import unittest

from nodes.prompt_parser import local_prompts


MASTER = """subject_definitions:
GLOBAL SUBJECT

summary:
GLOBAL SUMMARY

detailed_description:
GLOBAL STYLE
[Shot 1]: BODY ONE
TRANSITION: CUT
[Shot 2] at 00:05: BODY TWO
[Shot 3]: BODY THREE
[Shot 4] at 00:15: BODY FOUR

overall_soundscape:
GLOBAL SOUND

non_diegetic_music:
GLOBAL MUSIC"""


class PromptTests(unittest.TestCase):
    def test_prompt_split_retains_globals_and_only_selected_body(self):
        prompts = local_prompts(MASTER, 4)
        words = ["ONE", "TWO", "THREE", "FOUR"]
        for index, prompt in enumerate(prompts):
            self.assertIn("GLOBAL SUBJECT", prompt)
            self.assertIn("GLOBAL STYLE", prompt)
            self.assertIn("GLOBAL SOUND", prompt)
            self.assertIn("GLOBAL MUSIC", prompt)
            self.assertIn("[Shot 1] at 00:00:", prompt)
            self.assertIn(f"BODY {words[index]}", prompt)
            self.assertEqual(prompt.count("BODY "), 1)
        self.assertIn("TRANSITION: CUT", prompts[0])

    def test_prompt_count_mismatch_fails_before_rendering(self):
        with self.assertRaisesRegex(ValueError, r"require 4 shots.*contains 3"):
            local_prompts(MASTER.replace("[Shot 4] at 00:15: BODY FOUR\n", ""), 4)
