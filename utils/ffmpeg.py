# Copyright (C) 2026 Michele Condo'
# This file is part of ComfyUI MiniMax H3 Music Video.
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess

import torch


def ffmpeg_path(configured: str = "") -> str:
    requested = configured.strip()
    executable = (shutil.which(requested) or requested) if requested else shutil.which("ffmpeg")
    if not executable or not Path(executable).is_file():
        raise RuntimeError("ffmpeg was not found; install ffmpeg or set its full path in Advanced Settings")
    return executable


def _run(command: list[str], action: str):
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "unknown ffmpeg error"
        raise RuntimeError(f"ffmpeg failed while {action}: {detail}")


def save_silent_video(frames: torch.Tensor, path: Path, fps: float, executable: str):
    if frames.ndim != 4 or frames.shape[-1] < 3:
        raise ValueError("Decoded video must be a BHWC image batch")
    height, width = int(frames.shape[1]), int(frames.shape[2])
    path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        executable, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s:v", f"{width}x{height}", "-r", f"{fps:.8f}", "-i", "-",
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for frame in frames:
            data = frame[..., :3].detach().float().cpu().clamp(0, 1).mul(255).round().to(torch.uint8).contiguous().numpy()
            process.stdin.write(data.tobytes())
        process.stdin.close()
        error = process.stderr.read().decode("utf-8", "replace")
        return_code = process.wait()
    except Exception:
        process.kill()
        raise
    if return_code:
        raise RuntimeError(f"ffmpeg failed while saving silent shot video: {error.strip().splitlines()[-1]}")


def numeric_shot_order(files: list[Path]) -> list[Path]:
    def key(path):
        match = re.search(r"shot_(\d+)", path.stem)
        return int(match.group(1)) if match else 2**31
    return sorted(files, key=key)


def concatenate_silent_videos(files: list[Path], destination: Path, executable: str):
    if not files:
        raise ValueError("No completed shot videos are available for assembly")
    destination.parent.mkdir(parents=True, exist_ok=True)
    files = numeric_shot_order(files)
    concat_file = destination.parent / "shot_concat.txt"
    concat_file.write_text("".join(f"file '{str(path.resolve()).replace("'", "'\\''")}'\n" for path in files), encoding="utf-8")
    copy_command = [executable, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-an", "-c", "copy", str(destination)]
    result = subprocess.run(copy_command, capture_output=True, text=True, check=False)
    if result.returncode:
        _run([executable, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-an", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(destination)], "re-encoding shot concatenation")
    concat_file.unlink(missing_ok=True)


def mux_master_audio(silent_video: Path, master_audio: Path, destination: Path, executable: str):
    _run([
        executable, "-hide_banner", "-loglevel", "error", "-y", "-i", str(silent_video), "-i", str(master_audio),
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", str(destination),
    ], "muxing the original master audio")


def mux_scene(silent_video: Path, audio: Path, destination: Path, executable: str):
    mux_master_audio(silent_video, audio, destination, executable)


def assemble_final(files: list[Path], master_audio: Path, silent_video: Path, destination: Path, executable: str):
    concatenate_silent_videos(files, silent_video, executable)
    mux_master_audio(silent_video, master_audio, destination, executable)
