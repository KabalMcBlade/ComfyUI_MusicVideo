# Copyright (C) 2026 Michele Condo'
# This file is part of ComfyUI MiniMax H3 Music Video.
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import torch

from .node_ops import call_node


REQUIRED_NODES = (
    "LoadAudio", "LoadImage", "UNETLoader", "CLIPLoader", "VAELoader", "LoraLoaderModelOnly",
    "MiniMaxH3ReferenceToVideo", "MiniMaxH3SigmaShift", "VAEEncodeAudio",
    "MiniMaxH3MemoryEfficientSageAttentionPatch", "PathchSageAttentionKJ",
    "RandomNoise", "KSamplerSelect", "BasicScheduler", "BasicGuider", "SamplerCustomAdvanced", "VAEDecode", "ImageResizeKJv2",
)


def ordered_references(values):
    return {f"ref_image_{index}": image for index, image in enumerate(values) if image is not None}


def validate_nodes():
    import nodes
    missing = [name for name in REQUIRED_NODES if name not in nodes.NODE_CLASS_MAPPINGS]
    if missing:
        raise RuntimeError("Required ComfyUI nodes are missing: " + ", ".join(missing) + ". Update ComfyUI to a MiniMax H3 build.")


def separate_av_latent(av_latent):
    video_samples, audio_samples = av_latent["samples"].unbind()
    video = av_latent.copy()
    audio = av_latent.copy()
    video["samples"] = video_samples
    audio["samples"] = audio_samples
    if av_latent.get("noise_mask") is not None:
        video["noise_mask"], audio["noise_mask"] = av_latent["noise_mask"].unbind()
    return video, audio


def concat_av_latent(video_latent, audio_latent):
    import comfy.nested_tensor
    output = {**video_latent, **audio_latent}
    output["samples"] = comfy.nested_tensor.NestedTensor((video_latent["samples"], audio_latent["samples"]))
    video_mask = video_latent.get("noise_mask")
    audio_mask = audio_latent.get("noise_mask")
    if video_mask is not None or audio_mask is not None:
        if video_mask is None:
            video_mask = torch.ones_like(video_latent["samples"])
        if audio_mask is None:
            audio_mask = torch.ones_like(audio_latent["samples"])
        output["noise_mask"] = comfy.nested_tensor.NestedTensor((video_mask, audio_mask))
    return output


class MiniMaxPipeline:
    def __init__(self, model_name, text_encoder, video_vae_name, audio_vae_name, turbo_lora, steps):
        validate_nodes()
        model = call_node("UNETLoader", unet_name=model_name, weight_dtype="default")[0]
        model = call_node("MiniMaxH3MemoryEfficientSageAttentionPatch", model=model)[0]
        model = call_node("PathchSageAttentionKJ", model=model, sage_attention="auto", allow_compile=False)[0]
        if turbo_lora:
            model = call_node("LoraLoaderModelOnly", model=model, lora_name=turbo_lora, strength_model=1.0)[0]
        self.model = call_node("MiniMaxH3SigmaShift", model=model, shift_video=12.0, shift_audio=3.0)[0]
        self.clip = call_node("CLIPLoader", clip_name=text_encoder, type="minimax", device="default")[0]
        self.video_vae = call_node("VAELoader", vae_name=video_vae_name)[0]
        self.audio_vae = call_node("VAELoader", vae_name=audio_vae_name)[0]
        self.sampler = call_node("KSamplerSelect", sampler_name="er_sde")[0]
        self.steps = steps

    def render(self, prompt, audio, references, width, height, length, seed, decoding=None):
        conditioning, av_latent = call_node(
            "MiniMaxH3ReferenceToVideo", clip=self.clip, vae=self.video_vae, audio_vae=self.audio_vae,
            prompt=prompt, width=width, height=height, length=length, ref_image_size="max",
            ref_images=ordered_references(references), ref_audios={"ref_audio_0": audio},
        )[:2]
        video_latent, _ = separate_av_latent(av_latent)
        forced_audio = call_node("VAEEncodeAudio", audio=audio, vae=self.audio_vae)[0]
        forced_audio = forced_audio.copy()
        forced_audio["noise_mask"] = torch.zeros_like(forced_audio["samples"])
        latent = concat_av_latent(video_latent, forced_audio)
        noise = call_node("RandomNoise", noise_seed=seed)[0]
        guider = call_node("BasicGuider", model=self.model, conditioning=conditioning)[0]
        sigmas = call_node("BasicScheduler", model=self.model, scheduler="beta", steps=self.steps, denoise=1.0)[0]
        sampled = call_node("SamplerCustomAdvanced", noise=noise, guider=guider, sampler=self.sampler, sigmas=sigmas, latent_image=latent)[0]
        sampled_video, _ = separate_av_latent(sampled)
        if decoding:
            decoding()
        return call_node("VAEDecode", samples=sampled_video, vae=self.video_vae)[0]
