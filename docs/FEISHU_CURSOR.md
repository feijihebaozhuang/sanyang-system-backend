# 飞书 ↔ DeepSeek（原飞书-Cursor 桥接）

## 说明

桥接已从 **Cursor Agent CLI** 改为直接调用 **DeepSeek API**：

- 原因：Cursor Pro 配额有限且 agent CLI 不支持自定义模型
- 模型：`deepseek-v4-flash`（可通过环境变量 `DEEPSEEK_MODEL` 切换）
- API Key 来自 Cursor 桌面端原有的 DeepSeek 配置

## 飞书后台（此应用）

| 组件 | 飞书应用 | 作用 |
|------|----------|------|
| **OpenClaw** | 你已配好的另一个应用 | 不再改动 |
| **飞书-DeepSeek 桥接** | `cli_a96c20180038dbde` | 飞书消息 → **DeepSeek API** → 回飞书 |

凭证文件：`%USERPROFILE%\.config\feishu-agent-bridge\feishu.json`

1. [开放平台](https://open.feishu.cn/app/cli_a96c20180038dbde/event)
2. 事件订阅：**使用长连接接收事件**（不要 HTTP / ngrok）
3. 事件：`im.message.receive_v1`
4. 权限：`im:message`、`im:message:send_as_bot`、`im:chat`
5. 发布应用，添加机器人

## 一键配置

```powershell
cd D:\Desktop\sanyang-system
.\scripts\setup_feishu_cursor.ps1
```

自动：校验飞书凭证 → 安装依赖 → 创建桌面快捷方式 → 注册开机自启 → 启动桥接。

## 日常启动

- 双击桌面 **启动 Cursor飞书.bat**（前台，可看日志）
- 或登录 Windows 后计划任务 **SanyangFeishuCursor** 自动后台启动

手动：

```powershell
cd D:\Desktop\sanyang-system
.\scripts\start_feishu_cursor.ps1              # 前台
.\scripts\start_feishu_cursor.ps1 -Background  # 后台
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | Cursor settings 中的值 | DeepSeek API 密钥 |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | 模型名（也可用 `deepseek-v4-pro`） |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1` | API 地址 |

## Cursor 桌面端

桌面 Cursor 的 DeepSeek 模型已同步更新：

- 旧：`deepseek-chat` → 新：`deepseek-v4-flash`
- 同时支持 `deepseek-v4-pro`
- 旧模型名将在 2026-07-24 停用，已提前迁移

日志：`feishu_cursor.log`、`feishu_cursor.err.log`
