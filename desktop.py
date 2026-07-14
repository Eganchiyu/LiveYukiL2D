from __future__ import annotations

import ctypes
import threading
import time
from typing import Any

from server import HOST, PORT, load_config, main as run_server

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000


def set_mouse_passthrough(hwnd: int, enabled: bool) -> None:
    user32 = ctypes.windll.user32
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if enabled:
        style |= WS_EX_TRANSPARENT | WS_EX_LAYERED
    else:
        style &= ~WS_EX_TRANSPARENT
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)


class DesktopApi:
    def __init__(self, mouse_passthrough: bool) -> None:
        self._mouse_passthrough = mouse_passthrough
        self._window: Any | None = None

    def bind_window(self, window: Any) -> None:
        self._window = window

    def setIgnoreMouseEvent(self, ignored: bool) -> None:
        if not self._mouse_passthrough or self._window is None:
            return
        hwnd = getattr(self._window, "hwnd", None)
        if hwnd:
            set_mouse_passthrough(int(hwnd), ignored)


def start_server() -> None:
    run_server(handle_signals=False)


def main() -> None:
    try:
        import webview
    except ImportError as exc:
        raise SystemExit("缺少 pywebview。先运行：uv add pywebview 或 pip install pywebview") from exc

    config = load_config()
    pet_config = config.get("desktopPet", {})

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(0.8)

    api = DesktopApi(bool(pet_config.get("mousePassthrough", True)))
    window = webview.create_window(
        "LiveYukiL2D",
        f"http://{HOST}:{PORT}",
        width=int(pet_config.get("width", 420)),
        height=int(pet_config.get("height", 640)),
        x=pet_config.get("x"),
        y=pet_config.get("y"),
        frameless=bool(pet_config.get("frameless", True)),
        transparent=bool(pet_config.get("transparent", True)),
        on_top=bool(pet_config.get("alwaysOnTop", True)),
        resizable=bool(pet_config.get("resizable", True)),
        js_api=api,
    )
    api.bind_window(window)

    def on_loaded() -> None:
        if pet_config.get("mousePassthrough", True):
            api.setIgnoreMouseEvent(True)

    window.events.loaded += on_loaded
    webview.start(gui="edgechromium", debug=False)


if __name__ == "__main__":
    main()
