from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math

FPS = 24


@dataclass(frozen=True)
class Shot:
    index: int
    start: float
    end: float
    duration: float
    generation_frames: int
    trim_frames: int


def h3_generation_frames(duration: float) -> int:
    base = max(5, round(duration * FPS))
    return base + (5 - (base % 17)) % 17


def trim_frame_count(duration: float) -> int:
    return round(duration * FPS)


def plan_shots(duration: float, chunk_size: float) -> list[Shot]:
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Master audio duration must be greater than zero")
    if not math.isfinite(chunk_size) or chunk_size <= 0:
        raise ValueError("Chunk Size must be greater than zero")
    shots = []
    for index in range(math.ceil(duration / chunk_size)):
        start = index * chunk_size
        end = min(duration, (index + 1) * chunk_size)
        shot_duration = end - start
        shots.append(Shot(index + 1, start, end, shot_duration, h3_generation_frames(shot_duration), trim_frame_count(shot_duration)))
    return shots


def shots_to_render(shots: list[Shot], shot_index: int) -> list[Shot]:
    if shot_index == -1:
        return shots
    if shot_index < 1 or shot_index > len(shots):
        raise ValueError(f"Shot index must be -1 or between 1 and {len(shots)}")
    return [shots[shot_index - 1]]


def shot_list_json(shots: list[Shot]) -> str:
    return json.dumps([asdict(shot) for shot in shots], indent=2)
