# 三套机器人 — 各用各的，禁止混用

| 谁 | 飞书应用 App ID | 连接方式 | DeepSeek API Key | 启动方式 |
|----|-----------------|----------|------------------|----------|
| **OpenClaw** | `cli_a97ca4949b785cb5` | 长连接 | `sk-dcf59140596a492da2b6c78ea38604a6` | 计划任务 / `启动 OpenClaw.bat` |
| **Dify** | `cli_a96c15d3dcf8dbcd` | **HTTP** + ngrok | `sk-abaf056a56e745b396f0b7937ea503bb` | `启动 Dify.bat` + `start_feishu_dify.ps1` |
| **Cursor（我）** | `cli_a96c20180038dbde` | 长连接 | （用本机 **Cursor Agent**，不填 DeepSeek） | `启动 Cursor飞书.bat` |

## 飞书后台必配

### OpenClaw — [cli_a97ca](https://open.feishu.cn/app/cli_a97ca4949b785cb5/event)

- **使用长连接接收事件**
- 发布应用，添加机器人

### Dify — [cli_a96c15](https://open.feishu.cn/app/cli_a96c15d3dcf8dbcd/event)

- **将事件发送至开发者服务器**（不要长连接）
- 请求地址：**固定** `https://gizmo-ardently-nearness.ngrok-free.dev/api/webhook/feishu`（飞书后台填一次即可；重启 ngrok 不变）
- 事件：`im.message.receive_v1`
- Dify 网页：http://localhost → 设置 → DeepSeek → 填 `sk-abaf...`

### Cursor — [cli_a96c2018](https://open.feishu.cn/app/cli_a96c20180038dbde/event)

- **使用长连接接收事件**
- 发布应用，添加机器人

## 一键开通

```powershell
cd D:\Desktop\sanyang-system
.\scripts\setup_three_bots.ps1    # 只写配置
.\scripts\start_all_three.ps1   # 启动三套
```

桌面：`D:\Desktop\一键开通三套.bat`
