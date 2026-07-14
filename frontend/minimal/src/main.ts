import { updateModelConfig } from './WebSDK/src/lappdefine';
import { initializeLive2D } from './WebSDK/src/main';
import { LAppLive2DManager } from './WebSDK/src/lapplive2dmanager';
import { LAppDelegate } from './WebSDK/src/lappdelegate';
import * as LAppDefine from './WebSDK/src/lappdefine';

interface ModelInfo {
  name: string;
  url: string;
  kScale?: number;
  emotionMap?: Record<string, number | string>;
  defaultEmotion?: number | string;
  scrollToResize?: boolean;
  lookAtMouse?: boolean;
}

interface IncomingMessage {
  type: string;
  model_info?: ModelInfo;
  text?: string;
  expression?: number | string;
  audio?: string;
  actions?: { expressions?: Array<number | string> };
  display_text?: { text?: string; name?: string; avatar?: string };
}

const statusEl = document.getElementById('status')!;
const subtitleEl = document.getElementById('subtitle')!;
const canvasEl = document.getElementById('canvas') as HTMLCanvasElement;
const DEFAULT_MODEL: ModelInfo = {
  name: 'Yuki',
  url: 'http://127.0.0.1:18765/models/Yuki/Yuki.model3.json',
  kScale: 1.0,
  emotionMap: { neutral: 0 },
  defaultEmotion: 0,
};

function setStatus(text: string) {
  statusEl.textContent = text;
  console.log('[LiveYuki]', text);
}

function parseModelUrl(url: string): { baseUrl: string; modelDir: string; modelFileName: string } {
  const urlObj = new URL(url, window.location.href);
  const pathname = urlObj.pathname;
  const lastSlashIndex = pathname.lastIndexOf('/');
  const fullFileName = pathname.substring(lastSlashIndex + 1);
  const modelFileName = fullFileName.replace('.model3.json', '');
  const secondLastSlashIndex = pathname.lastIndexOf('/', lastSlashIndex - 1);
  const modelDir = pathname.substring(secondLastSlashIndex + 1, lastSlashIndex);
  const baseUrl = `${urlObj.protocol}//${urlObj.host}${pathname.substring(0, secondLastSlashIndex + 1)}`;
  return { baseUrl, modelDir, modelFileName };
}

function loadModel(modelInfo: ModelInfo = DEFAULT_MODEL) {
  const { baseUrl, modelDir, modelFileName } = parseModelUrl(modelInfo.url);
  setStatus(`加载模型: ${modelInfo.name || modelDir}`);
  console.log('[LiveYuki] model config', { baseUrl, modelDir, modelFileName, modelInfo });

  updateModelConfig(
    baseUrl,
    modelDir,
    modelFileName,
    Number(modelInfo.kScale ?? 1.0),
    modelInfo.lookAtMouse ?? true,
    modelInfo.scrollToResize ?? true
  );

  // 释放旧模型并重新初始化。Open-LLM-VTuber 原代码也这么做。
  try {
    if ((window as any).LAppLive2DManager?.releaseInstance) {
      (window as any).LAppLive2DManager.releaseInstance();
    }
  } catch (err) {
    console.warn('[LiveYuki] release old model failed:', err);
  }

  initializeLive2D();
  setTimeout(() => {
    const model = LAppLive2DManager.getInstance().getModel(0);
    setStatus(model ? '模型加载请求已发送，看画布是否出现 Yuki' : '模型管理器已启动，等待模型资源加载');
  }, 800);
}

function getAdapter(): any {
  return (window as any).getLAppAdapter?.();
}

function getWebviewApi(): any {
  return (window as any).pywebview?.api || (window as any).api || null;
}

async function getCanvasPointFromScreenPoint(cursor: CursorPosition): Promise<{ x: number; y: number } | null> {
  if (!canvasEl) return null;
  const rect = canvasEl.getBoundingClientRect();
  const api = getWebviewApi();
  let windowPos: CursorPosition = { x: window.screenX, y: window.screenY };
  if (api?.getWindowPosition) {
    windowPos = await api.getWindowPosition();
  }
  const x = cursor.x - Number(windowPos.x || 0) - rect.left;
  const y = cursor.y - Number(windowPos.y || 0) - rect.top;
  return { x, y };
}

function startMouseFollowLoop() {
  let running = false;
  const tick = async () => {
    const api = getWebviewApi();
    if (running || !api?.getCursorPosition || !LAppDefine.LookAtMouse) return;
    const model = LAppLive2DManager.getInstance().getModel(0);
    if (!model) return;

    running = true;
    try {
      const cursor = await api.getCursorPosition();
      const point = await getCanvasPointFromScreenPoint(cursor);
      const view = LAppDelegate.getInstance().getView();
      const rect = canvasEl.getBoundingClientRect();
      if (point && view && rect.width > 0 && rect.height > 0) {
        view.onTouchesMoved(point.x, point.y);
      }
    } catch {
      // ignore transient bridge errors
    } finally {
      running = false;
    }
  };

  window.setInterval(tick, 16);
}

function setExpression(expression: number | string) {
  const adapter = getAdapter();
  if (!adapter) {
    setStatus('adapter 未准备好，稍后再试');
    return;
  }
  try {
    if (typeof expression === 'number') {
      const name = adapter.getExpressionName(expression);
      if (name) adapter.setExpression(name);
      else setStatus(`模型没有 expression index=${expression}，Yuki 当前模型可能没有表情文件`);
    } else {
      adapter.setExpression(expression);
    }
  } catch (err) {
    console.warn('[LiveYuki] setExpression failed:', err);
    setStatus('设置表情失败，可能模型没有 expression 文件');
  }
}

function playTalkMotion() {
  const model = LAppLive2DManager.getInstance().getModel(0);
  if (!model) return;
  try {
    model.startRandomMotion('Talk', LAppDefine.PriorityNormal);
  } catch (err) {
    console.warn('[LiveYuki] Talk motion failed. This model probably has no motions.', err);
  }
}

function sayText(text: string, expression?: number | string) {
  subtitleEl.textContent = text;
  if (expression !== undefined) setExpression(expression);
  playTalkMotion();
}

function playAudioBase64(audioBase64: string, expression?: number | string, text?: string) {
  const model = LAppLive2DManager.getInstance().getModel(0) as any;
  if (!audioBase64) {
    if (text) sayText(text, expression);
    return;
  }

  if (expression !== undefined) setExpression(expression);
  if (text) subtitleEl.textContent = text;

  const audioDataUrl = `data:audio/wav;base64,${audioBase64}`;
  const audio = new Audio(audioDataUrl);
  audio.addEventListener('canplaythrough', () => {
    try {
      model?._wavFileHandler?.start(audioDataUrl);
    } catch (err) {
      console.warn('[LiveYuki] lip sync start failed:', err);
    }
    playTalkMotion();
    audio.play().catch((err) => console.warn('[LiveYuki] audio play failed:', err));
  });
  audio.addEventListener('ended', () => setStatus('音频播放结束'));
  audio.load();
}

function handleMessage(msg: IncomingMessage) {
  console.log('[LiveYuki] recv', msg);
  if (msg.type === 'set-model-and-conf' || msg.type === 'set-model') {
    if (msg.model_info) loadModel(msg.model_info);
    return;
  }

  if (msg.type === 'expression') {
    if (msg.expression !== undefined) setExpression(msg.expression);
    return;
  }

  if (msg.type === 'say') {
    sayText(msg.text || '', msg.expression);
    return;
  }

  if (msg.type === 'audio') {
    const expression = msg.actions?.expressions?.[0];
    const text = msg.display_text?.text || msg.text || '';
    playAudioBase64(msg.audio || '', expression, text);
  }
}

function connectWebSocket() {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsHost = window.location.hostname || '127.0.0.1';
  const wsUrl = `${wsProtocol}//${wsHost}:18765/ws`;
  const ws = new WebSocket(wsUrl);

  ws.addEventListener('open', () => setStatus(`WS 已连接: ${wsUrl}`));
  ws.addEventListener('close', () => {
    setStatus('WS 已断开，2 秒后重连');
    setTimeout(connectWebSocket, 2000);
  });
  ws.addEventListener('error', () => setStatus('WS 连接错误，确认 Python 服务是否启动'));
  ws.addEventListener('message', (event) => {
    try {
      handleMessage(JSON.parse(event.data));
    } catch (err) {
      console.warn('[LiveYuki] bad ws message:', event.data, err);
    }
  });

  (window as any).LiveYukiWS = ws;
}

function exposeDebug() {
  (window as any).LiveYuki = {
    loadModel,
    setExpression,
    sayText,
    playAudioBase64,
    manager: () => LAppLive2DManager.getInstance(),
    model: () => LAppLive2DManager.getInstance().getModel(0),
    adapter: getAdapter,
  };
}

document.getElementById('btn-reload')?.addEventListener('click', () => loadModel(DEFAULT_MODEL));
document.getElementById('btn-smile')?.addEventListener('click', () => setExpression(0));
document.getElementById('btn-info')?.addEventListener('click', () => {
  console.log('LiveYuki debug:', (window as any).LiveYuki);
  console.log('model:', (window as any).LiveYuki.model());
  setStatus('调试对象已输出到 console: window.LiveYuki');
});

exposeDebug();
loadModel(DEFAULT_MODEL);
connectWebSocket();
