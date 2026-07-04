/**
 * Feishu -> Dify 长连接桥接（WebSocket）
 * 
 * 用 feishu-agent-bridge 建立长连接到飞书，
 * 收到消息后调用 feishu_dify.py 处理。
 * 飞书后台选「使用长连接接收事件」即可，无需 ngrok。
 * 
 * 用法：node scripts/feishu_cursor/feishu-dify-ws.mjs
 */
import { spawn } from "node:child_process";
import { readFileSync, writeFileSync, appendFileSync, existsSync } from "node:fs";
import { createFeishuService } from "feishu-agent-bridge";

const ROOT = process.env.FEISHU_DIFY_WORKDIR || "D:/Desktop/sanyang-system";
const LOGFILE = ROOT + "/feishu_dify_ws.log";
const PIDFILE = ROOT + "/scripts/feishu_cursor/feishu-dify-ws.pid";

function log(msg) {
  const ts = new Date().toISOString();
  const line = `[${ts}] ${msg}`;
  console.log(msg);
  try { appendFileSync(LOGFILE, line + "\n"); } catch {}
}

log("Starting Feishu-Dify WS bridge...");
log("Workdir: " + ROOT);

// 从独立配置读取（避免 .env 解析问题）
const DIFY_WS_CONFIG_PATH = ROOT + "/scripts/feishu_cursor/feishu-dify-config.json";
let APP_ID = "", APP_SECRET = "";
try {
  const cfg = JSON.parse(readFileSync(DIFY_WS_CONFIG_PATH, "utf-8"));
  APP_ID = cfg.appId || "";
  APP_SECRET = cfg.appSecret || "";
  log("Config loaded from: " + DIFY_WS_CONFIG_PATH);
} catch (e) {
  log("WARN: cannot load config: " + e.message);
  // fallback: parse .env
  const ENV = loadEnv();
  APP_ID = ENV.FEISHU_APP_ID || "";
  APP_SECRET = ENV.FEISHU_APP_SECRET || "";
}

if (!APP_ID || !APP_SECRET) {
  log("ERROR: FEISHU_APP_ID or FEISHU_APP_SECRET not set in .env");
  process.exit(1);
}

log("App ID: " + APP_ID);
log("Dify API: http://127.0.0.1/v1");

/**
 * 调用 Python 脚本处理飞书消息（feishu_dify.py）
 * 返回 { success, reply }
 */
function handleMessageViaPython(content, senderId, chatId, chatType, messageId) {
  return new Promise((resolve) => {
    const pyArgs = [
      "-c", `
import sys, json
sys.path.insert(0, "${ROOT.replace(/\\/g, "\\\\")}")
from feishu_dify import _dify_chat, _send_text, _tenant_access_token, is_enabled

event = json.loads(sys.stdin.read())
query = event.get("text", "")
open_id = event.get("open_id", "")
chat_id = event.get("chat_id", "")
chat_type = event.get("chat_type", "p2p")
msg_id = event.get("message_id", "")

if not is_enabled():
    print(json.dumps({"success": False, "error": "bridge not enabled"}))
    sys.exit(0)

try:
    # 验证 token 有效性
    token = _tenant_access_token()
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
    sys.exit(0)

try:
    reply = _dify_chat(query, "feishu-" + open_id)
except Exception as e:
    reply = f"处理失败：{e}"

try:
    if chat_type == "p2p":
        _send_text(open_id, "open_id", reply)
    else:
        _send_text(chat_id, "chat_id", reply)
except Exception as e:
    reply = f"发送失败：{e}"

print(json.dumps({"success": True, "reply": reply[:200]}))
`,
    ];

    const child = spawn("python", pyArgs, {
      cwd: ROOT,
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
    });

    const input = JSON.stringify({
      text: content,
      open_id: senderId,
      chat_id: chatId,
      chat_type: chatType,
      message_id: messageId,
    });

    let out = "";
    let err = "";

    child.stdout.on("data", (d) => { out += d.toString(); });
    child.stderr.on("data", (d) => { err += d.toString(); });

    const timer = setTimeout(() => {
      child.kill();
      resolve({ success: false, error: "timeout" });
    }, 300000);

    child.on("close", (code) => {
      clearTimeout(timer);
      if (err) log("Python stderr: " + err.slice(0, 300));
      try {
        const result = JSON.parse(out.trim());
        resolve(result);
      } catch {
        resolve({ success: false, error: out.slice(0, 200) || err.slice(0, 200) || "unknown" });
      }
    });

    child.stdin.write(input);
    child.stdin.end();
  });
}

// 保存 PID
try { writeFileSync(PIDFILE, String(process.pid)); } catch {}

const service = await createFeishuService({
  transport: "ws",
  onMessage: async (msg) => {
    if (!msg.shouldReply) return;
    const chatId = msg.chatId;
    const content = msg.content;
    const msgId = msg.messageId;
    const chatType = msg.chatType || "p2p";
    log(`WS msg from=${msg.sender?.senderId || "?"} chat=${chatId} preview=${(content || "").slice(0, 60)}`);
    
    try {
      const result = await handleMessageViaPython(
        content,
        msg.sender?.senderId || "unknown",
        chatId,
        chatType,
        msgId
      );
      log(`Result: ${JSON.stringify(result)}`);
    } catch (e) {
      log("Handler error: " + e.message);
    }
  },
  onError: (err) => {
    log("Service error: " + (err?.message || JSON.stringify(err)));
  },
});

log("Bridge entered running state.");

// 保持运行
process.on("SIGTERM", () => {
  log("SIGTERM received, shutting down...");
  process.exit(0);
});
