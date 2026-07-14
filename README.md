# LiveYukiL2D

一个最小 Live2D 加载/通信实验，用来验证 `D:\Projects\Yuki` 里的 Yuki 模型能不能跑起来。

## 当前已做

已复制 Yuki 模型到：

```text
models/Yuki/
  Yuki.model3.json
  Yuki.moc3
  Yuki.physics3.json
  Yuki.cdi3.json
  Yuki.1024/texture_00.png
```

已创建最小前端：

```text
frontend/minimal/
```

已创建 Python 服务：

```text
server.py
main.py
```

## 模型可用性

`D:\Projects\Yuki` 这个模型可以先用于“加载显示”：

- 有 `.model3.json`
- 有 `.moc3`
- 有 texture
- 有 physics

但是它当前没有：

- `.exp3.json` 表情文件
- `.motion3.json` 动作文件

所以：

- 模型本体应该能显示。
- `expression=0` 这种表情测试大概率没明显效果。
- `Talk` motion / tap motion 大概率没明显动作。
- 如果 model3 的 LipSync 参数列表为空，音频唇同步也可能没效果。

先验证显示，再考虑补表情/动作资源。

## 启动方式

在项目根目录：

```bash
cd D:/Projects/LiveYukiL2D
uv sync
uv run python main.py
```

如果不用 uv：

```bash
cd D:/Projects/LiveYukiL2D
pip install aiohttp
python main.py
```

然后浏览器打开：

```text
http://127.0.0.1:18765
```

页面会自动加载：

```text
http://127.0.0.1:18765/models/Yuki/Yuki.model3.json
```

## 前端工程说明

前端源码在：

```text
frontend/minimal/
```

它是一个 Vite + TypeScript 的最小页面，不用 React。

关键文件：

```text
frontend/minimal/index.html
frontend/minimal/src/main.ts
frontend/minimal/src/WebSDK/src/lappdefine.ts
frontend/minimal/src/WebSDK/src/main.ts
frontend/minimal/src/WebSDK/src/lappmodel.ts
```

前端依赖完整 Cubism SDK：

```text
frontend/minimal/src/WebSDK/Core
frontend/minimal/src/WebSDK/Framework
frontend/minimal/src/WebSDK/src
```

## 通信接口

Python 服务端口：

```text
127.0.0.1:18765
```

WebSocket：

```text
ws://127.0.0.1:18765/ws
```

### 1. 重新加载模型

浏览器打开：

```text
http://127.0.0.1:18765/api/model
```

会向所有前端广播：

```json
{
  "type": "set-model",
  "model_info": {
    "name": "Yuki",
    "url": "http://127.0.0.1:18765/models/Yuki/Yuki.model3.json"
  }
}
```

### 2. 发送一句话

浏览器打开：

```text
http://127.0.0.1:18765/api/say?text=你好呀我是Yuki
```

带表情索引：

```text
http://127.0.0.1:18765/api/say?text=测试表情&expression=0
```

注意：当前 Yuki 模型没有 expression 文件，所以表情可能无效果。

### 3. 发送音频

POST JSON 到：

```text
http://127.0.0.1:18765/api/audio
```

示例 body：

```json
{
  "path": "cache/hello.wav",
  "text": "你好呀",
  "expression": 0
}
```

或者直接传 base64：

```json
{
  "audio": "base64-wav...",
  "text": "你好呀",
  "expression": 0
}
```

## 浏览器 Console 调试

页面会暴露：

```js
window.LiveYuki
```

可用：

```js
LiveYuki.model()
LiveYuki.adapter()
LiveYuki.sayText('测试')
LiveYuki.setExpression(0)
LiveYuki.loadModel({
  name: 'Yuki',
  url: 'http://127.0.0.1:18765/models/Yuki/Yuki.model3.json',
  kScale: 1.0
})
```

## 如果看不到模型

优先看浏览器 DevTools Console / Network：

1. `.model3.json` 是否 200
2. `.moc3` 是否 200
3. `texture_00.png` 是否 200
4. 是否报 WebGL / Cubism Core 错误

常见问题：

- 没有加载 `live2dcubismcore.min.js`
- 模型路径不对
- canvas 宽高为 0
- 浏览器阻止了某些本地资源请求

当前入口已经用 Python 服务统一托管资源，正常不应该有 CORS 问题。

## 和 Open-LLM-VTuber 的关系

这是从 Open-LLM-VTuber 抽出来的最小验证版，只保留：

- Live2D 渲染
- 模型加载
- WebSocket 通信
- 简单文字/音频消息入口

不包含：

- ASR
- TTS
- LLM Agent
- 聊天历史
- Electron 桌面壳
