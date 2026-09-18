# Copyright (C) 2026 Michele Condo'
# This file is part of ComfyUI MiniMax H3 Music Video.
# SPDX-License-Identifier: GPL-3.0-only

import torch
import unittest

from utils.audio import slice_audio


class AudioTests(unittest.TestCase):
    def test_audio_slices_have_no_gaps_or_overlap(self):
        waveform = torch.arange(1908, dtype=torch.float32).reshape(1, 1, -1)
        audio = {"waveform": waveform, "sample_rate": 100}
        ranges = [(0, 5), (5, 10), (10, 15), (15, 19.08)]
        chunks = [slice_audio(audio, start, end) for start, end in ranges]
        self.assertEqual([chunk["waveform"].shape[-1] for chunk in chunks], [500, 500, 500, 408])
        self.assertTrue(torch.equal(torch.cat([chunk["waveform"] for chunk in chunks], dim=-1), waveform))
        self.assertNotEqual(chunks[0]["waveform"].data_ptr(), waveform.data_ptr())
