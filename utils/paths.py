# Copyright (C) 2026 Michele Condo'
# This file is part of ComfyUI MiniMax H3 Music Video.
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


def safe_project_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._ -]+", "_", value.strip()).strip(" .")
    if not value:
        raise ValueError("Project name cannot be empty")
    return value[:96]


@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    @classmethod
    def in_comfy_output(cls, output_root: str, project: str):
        base = Path(output_root).resolve() / "MiniMaxH3MusicVideo"
        root = (base / safe_project_name(project)).resolve()
        if base != root and base not in root.parents:
            raise ValueError("Invalid project output path")
        return cls(root)

    @property
    def shots(self): return self.root / "shots"
    @property
    def final_video(self): return self.root / "final_music_video.mp4"
    @property
    def silent_concat(self): return self.root / "concatenated_silent.mp4"

    def shot(self, index: int): return self.shots / f"shot_{index:03d}.mp4"
    def shot_preview(self, index: int): return self.shots / f"shot_{index:03d}_preview.mp4"
    def create(self): self.shots.mkdir(parents=True, exist_ok=True)
