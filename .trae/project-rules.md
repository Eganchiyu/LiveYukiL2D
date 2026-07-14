# LiveYukiL2D 项目公约与规则

## 项目定位

LiveYukiL2D 是一个最小 Live2D 加载与通信验证项目，用于验证 Yuki 模型在本地 Python 服务和 Vite 前端中的显示、WebSocket 通信、文本消息和音频消息能力。

## 目录职责

- `server.py`：Python aiohttp 服务入口，负责静态资源托管、模型资源托管、WebSocket 广播和测试 API。
- `main.py`：项目启动薄入口，只调用 `server.main()`。
- `liveyuki_l2d/`：后端协议辅助代码，放置可复用的消息构造逻辑。
- `models/`：Live2D 模型资源目录，保持模型文件结构与 `.model3.json` 引用一致。
- `frontend/minimal/`：最小前端工程，负责 Live2D 渲染、模型加载、WebSocket 接收和浏览器调试接口。
- `frontend/vendor/`：外部参考或拷贝代码，除同步上游或明确需要外，不做业务修改。
- `docs/`：项目说明、文件说明、接口说明和维护文档。

## Python 规则

- Python 版本以 `.python-version` 为准，当前为 `3.13`；`pyproject.toml` 保持最低兼容 `>=3.10`。
- 依赖优先通过 `uv` 管理，修改 Python 依赖时同步更新 `pyproject.toml` 和 `uv.lock`。
- 服务端默认监听 `127.0.0.1:18765`，如需改动端口，应同步更新 README、前端默认模型地址和相关文档。
- WebSocket 消息结构应保持简单明确，新增消息类型时优先补充到 `liveyuki_l2d/protocol.py`。
- 对外输入边界需要做路径安全和资源存在性检查；内部调用不做过度防御。

## 前端规则

- `frontend/minimal/` 是 Vite + TypeScript 最小工程，不引入 React 等额外框架，除非项目目标明确变化。
- Live2D SDK 相关代码尽量保持原始结构，业务适配优先放在 `frontend/minimal/src/main.ts` 或独立适配层。
- 前端默认连接本地服务 `127.0.0.1:18765`，不要随意改为公网地址。
- 构建产物位于 `frontend/minimal/dist/`，服务端当前从该目录托管页面。

## Live2D 模型资源规则

- `models/Yuki/` 中的 `.model3.json`、`.moc3`、贴图、物理文件必须保持相对路径可用。
- 当前 Yuki 模型没有 `.exp3.json` 和 `.motion3.json`，不要假设表情或动作一定有效。
- 调整模型缩放、初始位置、交互配置时，优先修改服务端 `YUKI_MODEL_INFO`，并同步说明文档。

## 文档规则

- 根目录文件职责说明维护在 `docs/root-files.md`。
- 修改启动方式、端口、API、目录职责或模型资源结构时，同步更新 README 和 docs 中对应文档。
- 文档内容以中文为主，命令和路径保持可复制。

## Git 与生成文件规则

- 不提交 `.venv/`、`__pycache__/`、构建缓存等本地生成文件。
- 若决定提交前端构建产物，需要明确它是服务端运行所依赖的静态页面，并避免混入无关产物。
- 不在仓库中提交私钥、令牌、个人配置、临时音频缓存或大体积无关文件。

## 修改原则

- 优先做最小必要修改，不做与当前需求无关的重构。
- 修改现有行为前先阅读相关文件，确认调用链和端口、路径依赖。
- 外部拷贝代码和 SDK 文件谨慎改动，必要时在项目适配层解决。