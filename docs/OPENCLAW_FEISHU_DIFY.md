# Open 助手（OpenClaw 飞书机器人）接 Dify

飞书里的 **Open 助手** 对应 OpenClaw 配置里的应用：

- App ID：`cli_a96c15d3dcf8dbcd`（见 `~/.openclaw/openclaw.json` → `channels.feishu`）

要让用户在飞书里 @ 的还是这个机器人，但 **回答由 Dify 生成**，用本仓库桥接即可（不必新建飞书应用）。

## 方式一：桥接（推荐，最简单）

飞书 → ngrok → `feishu_dify.py` → Dify API → 飞书回复。

### 1. 关掉 OpenClaw 飞书收消息（避免和长连接抢同一个应用）

编辑 `C:\Users\Administrator\.openclaw\openclaw.json`：

```json
"channels": {
  "feishu": {
    "enabled": false,
    ...
  }
}
```

保存后 **重启 OpenClaw Gateway**（任务管理器里停掉 `openclaw gateway` 再开，或你平时的启动方式）。

> 只关 `channels.feishu.enabled`，不用卸 OpenClaw；其它能力不受影响。

### 2. 飞书后台改成 HTTP 回调（一次性）

[打开该应用 → 事件与回调](https://open.feishu.cn/app/cli_a96c15d3dcf8dbcd/event)

- 订阅方式：**将事件发送至开发者服务器**（不要「长连接」）
- 请求地址：运行下面脚本后剪贴板里的地址  
  `https://xxxx.ngrok-free.app/api/webhook/feishu`
- 事件：`im.message.receive_v1`
- 保存并通过 URL 校验

### 3. 本机 `.env`（项目根目录，已配 Open 助手 + Dify）

```env
FEISHU_DIFY_ENABLED=true
FEISHU_APP_ID=cli_a96c15d3dcf8dbcd
FEISHU_APP_SECRET=（与 openclaw.json 一致）
DIFY_API_BASE=http://127.0.0.1/v1
DIFY_API_KEY=app-xxx   # Dify 应用「Feishu Bot」的 API Key
```

Dify 应用若未配好工作流/模型，可暂时保持 `FEISHU_USE_OLLAMA_FALLBACK=true` 用本机 Ollama 顶一下。

### 4. 启动

```powershell
cd D:\Desktop\sanyang-system
.\scripts\start_feishu_dify.ps1
```

浏览器打开 `http://127.0.0.1:5099/` 应显示 `"enabled": true`。  
在飞书 **@Open 助手** 发消息测试。

### 5. 确认 Dify 在跑（WSL）

```powershell
wsl bash -c "cd /opt/services/dify/docker && docker compose ps"
```

浏览器：`http://localhost/apps` → 打开 **Feishu Bot** → 配置模型并 **发布** 工作流（当前为空图时 API 会报 `app_unavailable`，桥接会走 Ollama 回退）。

---

## 方式二：继续用 OpenClaw 大脑（高级）

若希望飞书仍走 OpenClaw Agent（工具、记忆等），把 **模型后端** 换成 Dify，需要 Dify 提供 OpenAI 兼容接口（例如社区 [dify2openai](https://github.com/yinheli/dify2openai)），再在 `openclaw.json` 里加 `models.providers` 指向 `http://127.0.0.1:8001/v1`。  
配置量较大，一般「只要 Dify 问答」用 **方式一** 即可。

---

## 对照

| 项目 | OpenClaw 飞书开着 | 方式一桥接 |
|------|-------------------|------------|
| 飞书机器人 | 同一个 Open 助手 | 同一个 |
| 谁生成回复 | DeepSeek 等 | **Dify**（或 Ollama 回退） |
| 事件接收 | 长连接 | **HTTP + ngrok** |
