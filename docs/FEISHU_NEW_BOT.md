# 新建飞书机器人（专用 Dify，不用 OpenClaw）

与 OpenClaw 的飞书应用 **完全分开**：在飞书后台新建一个企业自建应用，只给本仓库桥接用。

## 一、在飞书创建新应用

1. 打开 [飞书开发者后台](https://open.feishu.cn/app) → **创建企业自建应用**
2. 名称建议：`Dify 助手`（任意）
3. **添加应用能力** → 开启 **机器人**
4. **权限管理** → 批量开通至少：
   - `im:message`
   - `im:message:send_as_bot`
   - `im:message.group_at_msg:readonly`（群聊 @ 时需要）
5. **事件与回调**：
   - 订阅方式：**将事件发送至开发者服务器**（不要选「使用长连接接收事件」）
   - 请求地址：运行 `scripts\start_feishu_dify.ps1` 后剪贴板里的  
     `https://xxxx.ngrok-free.app/api/webhook/feishu`
   - 添加事件：`im.message.receive_v1`
   - 若启用加密：把 **Encrypt Key**、**Verification Token** 抄到 `.env`
6. **凭证与基础信息**：复制 **App ID**、**App Secret**
7. **版本管理与发布** → 创建版本并发布（企业内部可用）
8. 在飞书里把该机器人 **拉进群** 或允许成员 **单聊**

## 二、把凭证发给维护人员 / 写入 `.env`

项目根目录 `.env`（勿提交 Git）：

```env
FEISHU_DIFY_ENABLED=true
FEISHU_APP_ID=cli_新应用的
FEISHU_APP_SECRET=新应用的密钥
FEISHU_VERIFICATION_TOKEN=事件订阅页（未开加密可留空）
FEISHU_ENCRYPT_KEY=事件订阅页（未开加密可留空）

DIFY_API_BASE=http://127.0.0.1/v1
DIFY_API_KEY=app-xxx
```

改完后重启桥接：

```powershell
cd D:\Desktop\sanyang-system
.\scripts\start_feishu_dify.ps1
```

## 三、与 OpenClaw 的关系

| 项目 | OpenClaw 飞书 | 本桥接（新机器人） |
|------|----------------|-------------------|
| 飞书应用 | `openclaw.json` 里那一个 | **新建的另一个 App ID** |
| 收消息 | 多为长连接 | **HTTP Webhook + ngrok** |
| 可同时用 | 可以，两个不同应用互不影响 | |

旧应用 `cli_a96c15d3dcf8dbcd` 可继续在 OpenClaw 用；Dify 专用请只用 **新应用** 的 ID/Secret。
