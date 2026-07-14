"""Minimal Live2D websocket protocol helpers.

These helpers mirror the useful subset of Open-LLM-VTuber's frontend protocol:
- set-model-and-conf: tell frontend which Live2D model to load
- audio: play audio, set expression, trigger lip sync / talk motion
- control: conversation state hints
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any


def set_model_message(model_info: dict[str, Any], conf_name: str = "default", conf_uid: str = "default") -> dict[str, Any]:
    return {
        "type": "set-model-and-conf",
        "model_info": model_info,
        "conf_name": conf_name,
        "conf_uid": conf_uid,
    }


def control_message(text: str) -> dict[str, str]:
    return {"type": "control", "text": text}


def full_text_message(text: str) -> dict[str, str]:
    return {"type": "full-text", "text": text}


def audio_message(
    audio_wav_path: str | Path | None = None,
    text: str = "",
    expression: int | str | None = None,
    speaker_name: str = "Yuki",
    avatar: str = "",
) -> dict[str, Any]:
    """Build an audio message compatible with the copied frontend use-audio-task.ts.

    If audio_wav_path is None or missing, sends text-only audio payload.
    expression can be an expression index (int) or expression name (str).
    """
    audio_b64 = ""
    if audio_wav_path:
        path = Path(audio_wav_path)
        if path.exists():
            audio_b64 = base64.b64encode(path.read_bytes()).decode("ascii")

    actions: dict[str, Any] = {}
    if expression is not None:
        actions["expressions"] = [expression]

    return {
        "type": "audio",
        "audio": audio_b64,
        "volumes": [],
        "slice_length": 0,
        "display_text": {
            "text": text,
            "name": speaker_name,
            "avatar": avatar,
        },
        "actions": actions,
    }
