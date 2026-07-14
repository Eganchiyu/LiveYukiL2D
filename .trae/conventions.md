# Trae 协作约定

## 工作方式

1. 修改代码前先阅读相关文件，避免凭空改动。
2. 优先编辑现有文件，只有确有必要时才创建新文件。
3. 保持改动聚焦当前需求，不顺手做无关重构。
4. 涉及端口、路径、API、启动命令时，同步更新文档。
5. 生成或修改文档时使用中文，代码标识、命令、路径保持原样。

## 常用命令

后端启动：

```bash
uv sync
uv run python main.py
```

不用 uv 时：

```bash
pip install aiohttp
python main.py
```

前端构建：

```bash
cd frontend/minimal
npm install
npm run build
```

访问地址：

```text
http://127.0.0.1:18765
```

## 验证重点

- 页面是否能打开 `http://127.0.0.1:18765`。
- 模型资源 `models/Yuki/Yuki.model3.json`、`.moc3`、贴图是否返回 200。
- WebSocket `ws://127.0.0.1:18765/ws` 是否连接成功。
- `/api/model`、`/api/say`、`/api/audio` 是否能向前端广播消息。

## 禁止事项

- 不提交 `.venv/`、`__pycache__/`、临时缓存和无关构建文件。
- 不把本地绝对路径写入业务配置，README 中示例路径除外。
- 不随意修改 `frontend/vendor/` 或 Live2D SDK 文件。
- 不假设当前模型具有表情和动作资源。