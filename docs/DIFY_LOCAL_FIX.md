# 本机 Dify 修复说明

## 一键启动/修复

```powershell
cd D:\Desktop\sanyang-system
.\scripts\start_dify.ps1
```

脚本会：启动 WSL Docker、修复 `/home/dify` 权限、将 **Feishu Bot** 设为 `advanced-chat`、检测 API。

## 当前状态（修复后）

| 项 | 说明 |
|----|------|
| 控制台 | http://localhost |
| API | http://127.0.0.1/v1 |
| 应用 | Feishu Bot（`advanced-chat`） |
| 已知问题 | 工作流 `graph` 为空 `{}`，需在 UI 里编排并发布 |
| 回退 | 飞书桥接在 Dify 失败时用本机 Ollama（`qwen2.5:0.5b`） |

## 在 Dify 里补全应用（必做一次）

1. 打开 http://localhost 登录。
2. **设置 → 模型供应商**：添加 **DeepSeek**（API Key）或 **Ollama**（`http://host.docker.internal:11434` 或 WSL 内 `http://ollama:11434`，以你环境为准）。
3. 进入应用 **Feishu Bot → 工作流**：拖入 **开始 → LLM → 回复**，选模型，**发布**。
4. **访问 API** 确认 API Key 与 `.env` 中 `DIFY_API_KEY` 一致。

## 与 OpenClaw 分工

- **OpenClaw**：飞书新应用 `cli_a97ca4949b785cb5`，长连接，计划任务 19001。
- **Dify 飞书桥接**：需**另一个**飞书应用 + HTTP 事件 + ngrok，`.env` 设 `FEISHU_DIFY_ENABLED=true` 后运行 `.\scripts\start_feishu_dify.ps1`。

同一飞书应用不能同时开 OpenClaw WebSocket 与 Dify HTTP 回调。
