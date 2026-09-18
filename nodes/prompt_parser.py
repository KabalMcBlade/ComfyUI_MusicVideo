# Copyright (C) 2026 Michele Condo'
# This file is part of ComfyUI MiniMax H3 Music Video.
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from dataclasses import dataclass
import re


SHOT_MARKER = re.compile(r"(?im)^[ \t]*\[Shot\s+\d+\](?:[ \t]+at[ \t]+\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?)?[ \t]*:?[ \t]*")
TRAILING_GLOBAL = re.compile(r"(?im)^[ \t]*(?:overall_soundscape|non_diegetic_music)[ \t]*:")


@dataclass(frozen=True)
class ParsedPrompt:
    prefix: str
    shots: tuple[str, ...]
    suffix: str


def parse_prompt(prompt: str) -> ParsedPrompt:
    text = str(prompt or "").strip()
    if not text:
        raise ValueError("Prompt is required")
    markers = list(SHOT_MARKER.finditer(text))
    if not markers:
        raise ValueError("Prompt must contain explicit [Shot N] sections")
    prefix = text[:markers[0].start()].rstrip()
    suffix_start = len(text)
    trailing = list(TRAILING_GLOBAL.finditer(text, markers[-1].end()))
    if trailing:
        suffix_start = trailing[0].start()
    bodies = []
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else suffix_start
        bodies.append(text[marker.end():end].strip())
    suffix = text[suffix_start:].strip() if suffix_start < len(text) else ""
    return ParsedPrompt(prefix, tuple(bodies), suffix)


def local_prompts(prompt: str, expected_shots: int) -> list[str]:
    parsed = parse_prompt(prompt)
    actual = len(parsed.shots)
    if actual != expected_shots:
        raise ValueError(f"Audio/chunk settings require {expected_shots} shots, but the prompt contains {actual} [Shot N] sections.")
    output = []
    for body in parsed.shots:
        parts = [part for part in (parsed.prefix, f"[Shot 1] at 00:00:\n{body}", parsed.suffix) if part]
        output.append("\n\n".join(parts))
    return output
