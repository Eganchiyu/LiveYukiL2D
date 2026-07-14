from __future__ import annotations

import base64
import ctypes
import ctypes.wintypes
import json
import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import unquote

try:
    from aiohttp import web, WSMsgType
except ImportError as exc:
    raise SystemExit(
        "缺少 aiohttp。先运行：uv add aiohttp 或 pip install aiohttp"
    ) from exc

ROOT = Path(__file__).resolve().parent
MODELS_DIR = ROOT / "models"
FRONTEND_DIR = ROOT / "frontend" / "minimal" / "dist"
CONFIG_PATH = ROOT / "config.json"
HOST = "127.0.0.1"
PORT = 18765

CLIENTS: set[web.WebSocketResponse] = set()

DEFAULT_CONFIG: dict[str, Any] = {
    "desktopPet": {
        "enabled": True,
        "width": 420,
        "height": 640,
        "x": None,
        "y": None,
        "transparent": True,
        "frameless": True,
        "alwaysOnTop": True,
        "resizable": True,
        "mousePassthrough": True,
        "lookAtMouse": True,
    },
    "model": {
        "kScale": 1.0,
        "scrollToResize": True,
    },
}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"config.json 格式错误：{exc}") from exc
    return deep_merge(DEFAULT_CONFIG, data)


def get_yuki_model_info() -> dict[str, Any]:
    config = load_config()
    model_config = config.get("model", {})
    pet_config = config.get("desktopPet", {})
    return {
        "name": "Yuki",
        "url": f"http://{HOST}:{PORT}/models/Yuki/Yuki.model3.json",
        "kScale": model_config.get("kScale", 1.0),
        "initialXshift": 0,
        "initialYshift": 0,
        "idleMotionGroupName": "Idle",
        "defaultEmotion": 0,
        "emotionMap": {"neutral": 0},
        "tapMotions": {},
        "pointerInteractive": True,
        "scrollToResize": model_config.get("scrollToResize", True),
        "lookAtMouse": pet_config.get("lookAtMouse", True),
        "desktopPet": pet_config,
    }


def json_response(data: Any, status: int = 200) -> web.Response:
    return web.Response(
        text=json.dumps(data, ensure_ascii=False, indent=2),
        status=status,
        content_type="application/json",
    )


def safe_join(base: Path, rel: str) -> Path:
    rel = unquote(rel).replace("\\", "/").lstrip("/")
    path = (base / rel).resolve()
    if not str(path).startswith(str(base.resolve())):
        raise web.HTTPForbidden(text="invalid path")
    return path


async def index(_: web.Request) -> web.Response:
    path = FRONTEND_DIR / "index.html"
    return web.FileResponse(path)


async def frontend_static(request: web.Request) -> web.StreamResponse:
    rel = request.match_info.get("path", "")
    path = safe_join(FRONTEND_DIR, rel)
    if path.is_dir():
        path = path / "index.html"
    if not path.exists():
        raise web.HTTPNotFound(text=f"not found: {rel}")
    return web.FileResponse(path)


async def model_static(request: web.Request) -> web.StreamResponse:
    rel = request.match_info.get("path", "")
    path = safe_join(MODELS_DIR, rel)
    if not path.exists() or not path.is_file():
        raise web.HTTPNotFound(text=f"not found: {rel}")

    ctype, _ = mimetypes.guess_type(str(path))
    if path.suffix == ".moc3":
        ctype = "application/octet-stream"
    elif path.name.endswith(".model3.json") or path.suffix == ".json":
        ctype = "application/json"
    elif path.suffix == ".png":
        ctype = "image/png"
    return web.FileResponse(path, headers={"Content-Type": ctype or "application/octet-stream"})


async def broadcast(message: dict[str, Any]) -> None:
    dead: list[web.WebSocketResponse] = []
    text = json.dumps(message, ensure_ascii=False)
    for ws in CLIENTS:
        if ws.closed:
            dead.append(ws)
            continue
        await ws.send_str(text)
    for ws in dead:
        CLIENTS.discard(ws)


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    CLIENTS.add(ws)
    print(f"[ws] client connected, total={len(CLIENTS)}")

    await ws.send_str(json.dumps({"type": "set-model", "model_info": get_yuki_model_info()}, ensure_ascii=False))
    await ws.send_str(json.dumps({"type": "say", "text": "Yuki 模型加载中..."}, ensure_ascii=False))

    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            print("[ws] recv:", msg.data)
        elif msg.type == WSMsgType.ERROR:
            print("[ws] error:", ws.exception())

    CLIENTS.discard(ws)
    print(f"[ws] client disconnected, total={len(CLIENTS)}")
    return ws


async def api_config(_: web.Request) -> web.Response:
    return json_response(load_config())


async def api_model(_: web.Request) -> web.Response:
    model_info = get_yuki_model_info()
    await broadcast({"type": "set-model", "model_info": model_info})
    return json_response({"ok": True, "model_info": model_info, "clients": len(CLIENTS)})


async def api_say(request: web.Request) -> web.Response:
    text = request.query.get("text", "你好，我是 Yuki")
    expr_raw = request.query.get("expression")
    expression: int | str | None = None
    if expr_raw is not None:
        try:
            expression = int(expr_raw)
        except ValueError:
            expression = expr_raw

    msg = {"type": "say", "text": text}
    if expression is not None:
        msg["expression"] = expression
    await broadcast(msg)
    return json_response({"ok": True, "sent": msg, "clients": len(CLIENTS)})


async def api_cursor(_: web.Request) -> web.Response:
    point = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
    return json_response({"x": point.x, "y": point.y})


async def api_audio(request: web.Request) -> web.Response:
    data = await request.json()
    audio_path = data.get("path")
    text = data.get("text", "")
    expression = data.get("expression")
    audio_b64 = data.get("audio", "")

    if audio_path and not audio_b64:
        path = Path(audio_path)
        if not path.is_absolute():
            path = ROOT / path
        if path.exists():
            audio_b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        else:
            return json_response({"ok": False, "error": f"audio path not found: {path}"}, 404)

    msg: dict[str, Any] = {
        "type": "audio",
        "audio": audio_b64,
        "volumes": [],
        "slice_length": 0,
        "display_text": {"text": text, "name": "Yuki", "avatar": ""},
        "actions": {},
    }
    if expression is not None:
        msg["actions"]["expressions"] = [expression]

    await broadcast(msg)
    return json_response({"ok": True, "sent_text": text, "has_audio": bool(audio_b64), "clients": len(CLIENTS)})


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/ws", websocket_handler)
    app.router.add_get("/api/config", api_config)
    app.router.add_get("/api/model", api_model)
    app.router.add_get("/api/say", api_say)
    app.router.add_get("/api/cursor", api_cursor)
    app.router.add_post("/api/audio", api_audio)
    app.router.add_get("/models/{path:.*}", model_static)
    app.router.add_get("/{path:.*}", frontend_static)
    return app


def main(handle_signals: bool = True) -> None:
    print(f"LiveYukiL2D server: http://{HOST}:{PORT}")
    print(f"Serving model: {get_yuki_model_info()['url']}")
    web.run_app(create_app(), host=HOST, port=PORT, handle_signals=handle_signals)


if __name__ == "__main__":
    main()
