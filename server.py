from __future__ import annotations

import asyncio
import base64
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
HOST = "127.0.0.1"
PORT = 18765

CLIENTS: set[web.WebSocketResponse] = set()

YUKI_MODEL_INFO: dict[str, Any] = {
    "name": "Yuki",
    "url": f"http://{HOST}:{PORT}/models/Yuki/Yuki.model3.json",
    "kScale": 1.0,
    "initialXshift": 0,
    "initialYshift": 0,
    "idleMotionGroupName": "Idle",
    "defaultEmotion": 0,
    "emotionMap": {"neutral": 0},
    "tapMotions": {},
    "pointerInteractive": True,
    "scrollToResize": True,
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

    # aiohttp sometimes does not know .moc3/.model3.json; set sane defaults.
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

    await ws.send_str(json.dumps({"type": "set-model", "model_info": YUKI_MODEL_INFO}, ensure_ascii=False))
    await ws.send_str(json.dumps({"type": "say", "text": "Yuki 模型加载中..."}, ensure_ascii=False))

    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            print("[ws] recv:", msg.data)
        elif msg.type == WSMsgType.ERROR:
            print("[ws] error:", ws.exception())

    CLIENTS.discard(ws)
    print(f"[ws] client disconnected, total={len(CLIENTS)}")
    return ws


async def api_model(_: web.Request) -> web.Response:
    await broadcast({"type": "set-model", "model_info": YUKI_MODEL_INFO})
    return json_response({"ok": True, "model_info": YUKI_MODEL_INFO, "clients": len(CLIENTS)})


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
    app.router.add_get("/api/model", api_model)
    app.router.add_get("/api/say", api_say)
    app.router.add_post("/api/audio", api_audio)
    app.router.add_get("/models/{path:.*}", model_static)
    app.router.add_get("/{path:.*}", frontend_static)
    return app


def main() -> None:
    print(f"LiveYukiL2D server: http://{HOST}:{PORT}")
    print(f"Serving model: {YUKI_MODEL_INFO['url']}")
    web.run_app(create_app(), host=HOST, port=PORT)


if __name__ == "__main__":
    main()
