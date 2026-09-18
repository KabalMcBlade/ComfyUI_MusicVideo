# Copyright (C) 2026 Michele Condo'
# This file is part of ComfyUI MiniMax H3 Music Video.
# SPDX-License-Identifier: GPL-3.0-only

from .nodes.minimax_music_video import MiniMaxH3MusicVideo

NODE_CLASS_MAPPINGS = {
    "MiniMaxH3MusicVideo": MiniMaxH3MusicVideo,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MiniMaxH3MusicVideo": "MiniMax H3 Music Video",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
