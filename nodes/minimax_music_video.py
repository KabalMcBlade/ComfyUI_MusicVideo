# Copyright (C) 2026 Michele Condo'
# This file is part of ComfyUI MiniMax H3 Music Video.
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import math
from pathlib import Path

from .minimax_pipeline import MiniMaxPipeline, validate_nodes
from .node_ops import call_node
from .planning import FPS, plan_shots, shots_to_render, shot_list_json
from .prompt_parser import local_prompts
from ..utils.audio import duration_seconds, save_wav, slice_audio
from ..utils.ffmpeg import assemble_final, ffmpeg_path, mux_scene, save_silent_video
from ..utils.paths import ProjectPaths


ASPECTS = {"16:9": (16, 9), "9:16": (9, 16), "1:1": (1, 1), "4:3": (4, 3), "3:4": (3, 4), "21:9": (21, 9)}
DEFAULT_MODEL = "minimax_h3_ref2va_pruned_nvfp4.safetensors"
DEFAULT_TEXT_ENCODER = "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"
DEFAULT_VIDEO_VAE = "minimax_h3_video_vae_int8_convrot.safetensors"
DEFAULT_AUDIO_VAE = "minimax_h3_audio_vae_fp32.safetensors"
DEFAULT_LORA = "MINIMAX\\minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors"


def resolution(aspect_ratio: str, megapixels: float, multiple: int = 32) -> tuple[int, int]:
    if aspect_ratio not in ASPECTS or not math.isfinite(megapixels) or megapixels <= 0:
        raise ValueError("Invalid MiniMax output resolution")
    wr, hr = ASPECTS[aspect_ratio]
    scale = math.sqrt(megapixels * 1024 * 1024 / (wr * hr))
    width = round(wr * scale / multiple) * multiple
    height = round(hr * scale / multiple) * multiple
    if width < multiple or height < multiple:
        raise ValueError("Invalid MiniMax output resolution")
    return width, height


def upscale_resolution(aspect_ratio: str) -> tuple[int, int]:
    if aspect_ratio not in ASPECTS:
        raise ValueError("Invalid MiniMax output aspect ratio")
    wr, hr = ASPECTS[aspect_ratio]
    if wr >= hr:
        return round(1080 * wr / hr), 1080
    return 1080, round(1080 * hr / wr)


def _progress(unique_id, shot, total, stage):
    try:
        from server import PromptServer
        PromptServer.instance.send_sync("minimax_h3_music_video_progress", {"node": unique_id, "shot": shot, "total": total, "stage": stage}, PromptServer.instance.client_id)
    except (ImportError, AttributeError):
        pass


def _interrupt():
    import comfy.model_management
    comfy.model_management.throw_exception_if_processing_interrupted()


def _validate_models(names):
    import folder_paths
    categories = ("diffusion_models", "text_encoders", "vae", "vae", "loras")
    for category, name in zip(categories, names):
        if name and folder_paths.get_full_path(category, name) is None:
            raise ValueError(f"Required MiniMax model file is missing: {name}")


class MiniMaxH3MusicVideo:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "master_audio": ("STRING", {"default": ""}),
            "chunk_size": ("FLOAT", {"default": 5.0, "min": 0.01, "max": 60.0, "step": 0.01}),
            "picture_1": ("STRING", {"default": ""}), "picture_2": ("STRING", {"default": ""}),
            "picture_3": ("STRING", {"default": ""}), "picture_4": ("STRING", {"default": ""}),
            "prompt": ("STRING", {"default": "", "multiline": True, "dynamicPrompts": False}),
            "aspect_ratio": (list(ASPECTS), {"default": "16:9"}),
            "megapixels": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 2.0, "step": 0.05}),
            "project_name": ("STRING", {"default": "minimax_h3_music_video"}),
            "global_seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            "steps": ("INT", {"default": 10, "min": 1, "max": 100}),
            "model_name": ("STRING", {"default": DEFAULT_MODEL}), "text_encoder": ("STRING", {"default": DEFAULT_TEXT_ENCODER}),
            "video_vae": ("STRING", {"default": DEFAULT_VIDEO_VAE}), "audio_vae": ("STRING", {"default": DEFAULT_AUDIO_VAE}),
            "turbo_lora": ("STRING", {"default": DEFAULT_LORA}), "ffmpeg_executable": ("STRING", {"default": ""}),
            "save_shot_previews": ("BOOLEAN", {"default": False}), "stitch_final_video": ("BOOLEAN", {"default": True}),
            "shot_index": ("INT", {"default": -1, "min": -1, "max": 0xffffffffffffffff}),
            "enable_upscale": ("BOOLEAN", {"default": False}),
        }, "hidden": {"unique_id": "UNIQUE_ID"}}

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("final_video_path", "shots_directory", "shot_list_json")
    FUNCTION = "render"
    OUTPUT_NODE = True
    CATEGORY = "Music Video"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def render(self, master_audio, chunk_size, picture_1, picture_2, picture_3, picture_4, prompt,
               aspect_ratio, megapixels, project_name, global_seed, steps, model_name, text_encoder,
               video_vae, audio_vae, turbo_lora, ffmpeg_executable, save_shot_previews,
               stitch_final_video, shot_index=-1, enable_upscale=False, unique_id=None):
        import folder_paths

        if not master_audio:
            raise ValueError("Master audio is required")
        reference_names = [value.strip() for value in (picture_1, picture_2, picture_3, picture_4) if value.strip()]
        if not reference_names:
            raise ValueError("At least one reference image is required")
        validate_nodes()
        _validate_models((model_name, text_encoder, video_vae, audio_vae, turbo_lora))
        executable = ffmpeg_path(ffmpeg_executable)
        audio = call_node("LoadAudio", audio=master_audio)[0]
        shots = plan_shots(duration_seconds(audio), chunk_size)
        prompts = local_prompts(prompt, len(shots))
        selected_shots = shots_to_render(shots, shot_index)
        width, height = resolution(aspect_ratio, megapixels)
        images = [call_node("LoadImage", image=name)[0] for name in reference_names]
        paths = ProjectPaths.in_comfy_output(folder_paths.get_output_directory(), project_name)
        paths.create()
        source_audio = Path(folder_paths.get_annotated_filepath(master_audio))
        pipeline = MiniMaxPipeline(model_name, text_encoder, video_vae, audio_vae, turbo_lora, steps)
        completed = []
        for shot in selected_shots:
            local_prompt = prompts[shot.index - 1]
            _interrupt()
            _progress(unique_id, shot.index, len(shots), "Preparing")
            chunk = slice_audio(audio, shot.start, shot.end)
            _progress(unique_id, shot.index, len(shots), "MiniMax sampling")
            frames = pipeline.render(local_prompt, chunk, images, width, height, shot.generation_frames, global_seed + shot.index - 1,
                                     decoding=lambda: _progress(unique_id, shot.index, len(shots), "Decoding"))
            _interrupt()
            if frames.shape[0] < shot.trim_frames:
                raise RuntimeError(f"Shot {shot.index} decoded only {frames.shape[0]} frames; {shot.trim_frames} are required")
            frames = frames[:shot.trim_frames].clone()
            if enable_upscale:
                upscale_width, upscale_height = upscale_resolution(aspect_ratio)
                _progress(unique_id, shot.index, len(shots), f"Upscaling to {upscale_width}x{upscale_height}")
                frames = call_node(
                    "ImageResizeKJv2", image=frames, width=upscale_width, height=upscale_height, upscale_method="lanczos",
                    keep_proportion="crop", pad_color="0, 0, 0", crop_position="center", divisible_by=2,
                    device="cpu", unique_id=unique_id,
                )[0]
            shot_path = paths.shot(shot.index)
            _progress(unique_id, shot.index, len(shots), "Saving")
            save_silent_video(frames, shot_path, FPS, executable)
            completed.append(shot_path)
            if save_shot_previews:
                chunk_wav = paths.shots / f"shot_{shot.index:03d}.wav"
                save_wav(chunk, chunk_wav)
                mux_scene(shot_path, chunk_wav, paths.shot_preview(shot.index), executable)
                chunk_wav.unlink(missing_ok=True)
            del chunk, frames
        final_path = ""
        if stitch_final_video and shot_index == -1:
            _interrupt()
            _progress(unique_id, len(shots), len(shots), "Stitching")
            assemble_final(completed, source_audio, paths.silent_concat, paths.final_video, executable)
            paths.silent_concat.unlink(missing_ok=True)
            final_path = str(paths.final_video)
        _progress(unique_id, len(shots), len(shots), "Complete")
        return (final_path, str(paths.shots), shot_list_json(shots))
