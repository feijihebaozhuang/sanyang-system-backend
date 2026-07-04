/**
 * Feishu -> DeepSeek API（长连接 WebSocket）
 *
 * 收到飞书消息后直接调用 DeepSeek API（OpenAI 兼容格式），
 * 不再依赖 Cursor Agent CLI（因 Cursor Pro 配额有限且不支持自定义模型）。
 *
 * 环境变量：
 *   DEEPSEEK_API_KEY   - DeepSeek API 密钥（默认读取 settings.json 中的值）
 *   DEEPSEEK_MODEL     - 模型名（默认 deepseek-v4-flash）
 *   DEEPSEEK_BASE_URL  - API 地址（默认 https://api.deepseek.com/v1）
 */
import { writeFileSync } from "node:fs";
import { createFeishuService } from "feishu-agent-bridge";

const WORKDIR = process.env.FEISHU_CURSOR_WORKDIR || "D:/Desktop/sanyang-system";
const LOGFILE = WORKDIR + "/feishu_cursor.log";

function log(msg) {
  const ts = new Date().toISOString();
  const line = `[${ts}] ${msg}`;
  console.log(msg);
  try { writeFileSync(LOGFILE, line + "\n", { flag: "a" }); } catch {}
}

// ---------- 配置 ----------

const DEEPSEEK_API_KEY =
  process.env.DEEPSEEK_API_KEY ||
  "sk-9a48f1ea984344fb8b72453aacb944cc";

const DEEPSEEK_BASE_URL =
  process.env.DEEPSEEK_BASE_URL || "https://api.deepseek.com/v1";

const MODEL = process.env.DEEPSEEK_MODEL || "deepseek-v4-flash";

// ---------- DeepSeek API 调用 ----------

async function callDeepSeek(prompt) {
  const url = `${DEEPSEEK_BASE_URL}/chat/completions`;
  const body = {
    model: MODEL,
    messages: [
      { role: "system", content: "你是一个智能助手。回答简洁准确，使用中文。" },
      { role: "user", content: prompt },
    ],
    stream: false,
    max_tokens: 4096,
    temperature: 0.7,
  };

  const resp = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${DEEPSEEK_API_KEY}`,
    },
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    const errText = await resp.text().catch(() => "(no body)");
    throw new Error(`DeepSeek API ${resp.status}: ${errText.slice(0, 200)}`);
  }

  const data = await resp.json();
  const content = data?.choices?.[0]?.message?.content || "";
  return content.slice(0, 3800) || "(no response)";
}

// ---------- 启动 ----------

log("Starting Feishu -> DeepSeek bridge...");
log("Workspace: " + WORKDIR);
log("Model: " + MODEL);
log("API: " + DEEPSEEK_BASE_URL);

const service = await createFeishuService({
  transport: "ws",
  onMessage: async (msg) => {
    if (!msg.shouldReply) return;
    const chatId = msg.chatId;
    const content = msg.content;
    const msgId = msg.messageId;
    log(`WS msg chatId=${chatId} msgId=${msgId} preview=${(content || "").slice(0, 60)}`);
    const sender = service.getSender();
    try {
      const reply = await callDeepSeek(content);
      log(`DeepSeek reply OK len=${reply.length}`);
      await sender.sendText(chatId, reply);
      log("Reply sent to " + chatId);
    } catch (e) {
      log("DeepSeek error: " + e.message);
      const errMsg = "处理失败：" + e.message.slice(0, 200);
      await sender.sendText(chatId, errMsg);
    }
  },
  onBotAdded: async (chatId) => {
    log("Bot added to chat " + chatId);
    const sender = service.getSender();
    await sender.sendText(chatId, "飞书-DeepSeek 桥接已连接。发送消息即可。");
  },
});

log("Bridge entered running state.");
await service.run();
