# Copyright (C) 2026 Michele Condo'
# This file is part of ComfyUI MiniMax H3 Music Video.
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import inspect


def _result(value):
    if hasattr(value, "result"):
        value = value.result
    if isinstance(value, dict) and "result" in value:
        value = value["result"]
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    return (value,)


def call_node(node_name: str, **kwargs):
    import nodes

    node_class = nodes.NODE_CLASS_MAPPINGS.get(node_name)
    if node_class is None:
        raise RuntimeError(f"Required ComfyUI node '{node_name}' is not installed")
    if hasattr(node_class, "execute"):
        callable_ = node_class.execute
    else:
        instance = node_class()
        function_name = getattr(node_class, "FUNCTION", None)
        if not function_name or not hasattr(instance, function_name):
            raise RuntimeError(f"Required node '{node_name}' has no callable execution method")
        callable_ = getattr(instance, function_name)
    signature = inspect.signature(callable_)
    accepted = {name: value for name, value in kwargs.items() if name in signature.parameters}
    missing = [name for name, parameter in signature.parameters.items() if name not in accepted and parameter.default is inspect.Parameter.empty and name not in ("self", "cls")]
    if missing:
        raise RuntimeError(f"Installed '{node_name}' interface is incompatible; missing inputs: {', '.join(missing)}")
    return _result(callable_(**accepted))
