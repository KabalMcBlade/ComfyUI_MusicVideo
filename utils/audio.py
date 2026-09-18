# Copyright (C) 2026 Michele Condo'
# This file is part of ComfyUI MiniMax H3 Music Video.
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from pathlib import Path
import wave

import numpy as np
import torch


def duration_seconds(audio: dict) -> float:
    try:
        waveform = audio["waveform"]
        sample_rate = int(audio["sample_rate"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Master audio could not be decoded") from error
    if sample_rate <= 0 or waveform.shape[-1] <= 0:
        raise ValueError("Master audio could not be decoded")
    return waveform.shape[-1] / sample_rate


def slice_audio(audio: dict, start_sec: float, end_sec: float) -> dict:
    sample_rate = int(audio["sample_rate"])
    start = round(start_sec * sample_rate)
    end = min(audio["waveform"].shape[-1], round(end_sec * sample_rate))
    if start < 0 or start >= end:
        raise ValueError("Requested shot audio range is empty")
    return {"waveform": audio["waveform"][..., start:end].clone(), "sample_rate": sample_rate}


def _pcm16(audio: dict) -> tuple[np.ndarray, int]:
    waveform = audio["waveform"].detach().float().cpu()
    while waveform.ndim > 2:
        waveform = waveform[0]
    if waveform.ndim == 1:
        waveform = waveform.unsqueeze(0)
    pcm = waveform.clamp(-1, 1).mul(32767).round().to(torch.int16).transpose(0, 1).contiguous().numpy()
    return pcm, int(audio["sample_rate"])


def save_wav(audio: dict, path: Path):
    pcm, sample_rate = _pcm16(audio)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(pcm.shape[1])
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())
