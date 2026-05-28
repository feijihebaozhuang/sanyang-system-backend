# 飞书 ↔ Cursor（不是 OpenClaw）

## 分工

| 组件 | 飞书应用 | 作用 |
|------|----------|------|
| **OpenClaw** | 你已配好的另一个应用 | 不再改动 |
| **Cursor 飞书桥接** | `cli_a96c20180038dbde` | 飞书消息 → 本机 **`agent` CLI**（非 cursor.exe）→ 回飞书 |

凭证文件：`%USERPROFILE%\.config\feishu-agent-bridge\feishu.json`

## 飞书后台（此应用）

1. [开放平台](https://open.feishu.cn/app/cli_a96c20180038dbde/event)
2. 事件订阅：**使用长连接接收事件**（不要 HTTP / ngrok）
3. 事件：`im.message.receive_v1`
4. 权限：`im:message`、`im:message:send_as_bot`、`im:chat`
5. 发布应用，添加机器人

## 一键配置（推荐）

```powershell
cd D:\Desktop\sanyang-system
.\scripts\setup_feishu_cursor.ps1
```

会自动：校验飞书凭证 → 安装依赖 → 创建桌面快捷方式 → 注册开机自启 → 启动桥接。

## 日常启动

- 双击桌面 **启动 Cursor飞书.bat**（前台，可看日志）
- 或登录 Windows 后计划任务 **SanyangFeishuCursor** 自动后台启动

手动：

```powershell
cd D:\Desktop\sanyang-system
.\scripts\start_feishu_cursor.ps1          # 前台
.\scripts\start_feishu_cursor.ps1 -Background  # 后台
```

电脑需 **已 `agent login`**（Cursor Agent CLI，不是编辑器登录）。未登录时双击 **登录 Cursor Agent.bat**。

首次安装 Agent CLI：

```powershell
irm 'https://cursor.com/install?win32=true' | iex
agent login
```

日志：`feishu_cursor.log`、`feishu_cursor.err.log`

## 说明

- Cursor 聊天窗口里的 AI **不会自动**收到飞书消息；靠本桥接调用 **Cursor Agent CLI**（命令名 `agent`，不是 `cursor`）。
- `sk-abaf...` 是 **Dify** 用，与飞书-Cursor 桥接无关。
