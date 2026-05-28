/**
 * 飞书 -> 本机 Cursor Agent CLI（不是 cursor.exe 编辑器）
 * 飞书后台：长连接 + im.message.receive_v1
 *
 * 前置：irm 'https://cursor.com/install?win32=true' | iex
 *       agent login   （或设置 CURSOR_API_KEY）
 */
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { createFeishuService } from "feishu-agent-bridge";

const WORKDIR = process.env.FEISHU_CURSOR_WORKDIR || "D:/Desktop/sanyang-system";
const AGENT_MODE = process.env.FEISHU_CURSOR_MODE || "ask";
const AGENT_BIN =
  process.env.CURSOR_AGENT_BIN ||
  (process.platform === "win32"
    ? `${process.env.LOCALAPPDATA || ""}/cursor-agent/agent.cmd`
    : "agent");

function resolveAgentBin() {
  if (existsSync(AGENT_BIN)) return AGENT_BIN;
  return "agent";
}

function runCursorAgent(prompt, senderId) {
  return new Promise((resolve, reject) => {
    const bin = resolveAgentBin();
    const args = [
      "-p",
      "--trust",
      "--mode",
      AGENT_MODE,
      "--workspace",
      WORKDIR,
      "--output-format",
      "text",
      prompt,
    ];
    const child = spawn(bin, args, {
      cwd: WORKDIR,
      shell: process.platform === "win32",
      env: { ...process.env, FEISHU_USER: senderId },
      windowsHide: true,
    });
    let out = "";
    let err = "";
    const timer = setTimeout(() => {
      child.kill("SIGTERM");
      reject(new Error("Cursor Agent 超时（5 分钟）"));
    }, 300000);
    child.stdout?.on("data", (d) => {
      out += d.toString();
    });
    child.stderr?.on("data", (d) => {
      err += d.toString();
    });
    child.on("error", (e) => {
      clearTimeout(timer);
      reject(
        new Error(
          `找不到 agent 命令：${e.message}\n请先安装：irm 'https://cursor.com/install?win32=true' | iex`
        )
      );
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      const text = (out || err || "").trim();
      if (/Authentication required|agent login/i.test(text)) {
        reject(
          new Error(
            "Cursor Agent 未登录。请在 PowerShell 运行：agent login\n或设置环境变量 CURSOR_API_KEY"
          )
        );
        return;
      }
      if (/Run with 'cursor -'/i.test(text)) {
        reject(
          new Error(
            "误用了 cursor.exe（编辑器），需要 Cursor Agent CLI。\n请运行：irm 'https://cursor.com/install?win32=true' | iex"
          )
        );
        return;
      }
      if (!text && code !== 0) {
        reject(new Error(`agent 退出码 ${code}`));
        return;
      }
      resolve(text.slice(0, 3800) || "（Agent 无文本输出）");
    });
  });
}

const service = await createFeishuService({
  transport: "ws",
  onMessage: async (msg) => {
    if (!msg.shouldReply) return;
    const sender = service.getSender();
    await sender.sendText(msg.chatId, "收到，Cursor Agent 处理中…");
    try {
      const reply = await runCursorAgent(msg.content, msg.senderId);
      await sender.sendText(msg.chatId, reply);
    } catch (e) {
      await sender.sendText(
        msg.chatId,
        `处理失败：${e.message}\n\n请确认：1) 已安装 agent CLI  2) 已 agent login  3) 飞书应用已开长连接`
      );
    }
  },
  onBotAdded: async (chatId) => {
    await service.getSender().sendText(
      chatId,
      "已连接 Cursor 飞书桥接（agent CLI）。直接发消息即可。\n首次使用请在电脑运行：agent login"
    );
  },
});

console.log("[feishu-cursor] WebSocket 启动，工作区:", WORKDIR);
console.log("[feishu-cursor] Agent:", resolveAgentBin(), "mode:", AGENT_MODE);
console.log("[feishu-cursor] 配置: ~/.config/feishu-agent-bridge/feishu.json");
await service.run();
