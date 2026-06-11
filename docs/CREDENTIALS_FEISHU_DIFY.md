# 飞书 / Dify / OpenClaw 凭证分工（勿混用）

## 两套东西，各干各的

| 凭证 | 给谁用 | 作用 |
|------|--------|------|
| **飞书 App ID + Secret**<br>`cli_a96c20180038dbde` / `8jSaUPBDhnMabpZAp67avwD4LVX1KuaC` | **OpenClaw**（飞书助手） | 飞书长连接收消息、发回复。配置在 `~/.openclaw/openclaw.json` |
| **API Key**<br>`sk-abaf056a56e745b396f0b7937ea503bb` | **Dify**（大模型） | 在 Dify 网页里当「模型供应商」的密钥，给 Dify 里的应用调用 LLM。**不要**写进 OpenClaw |

## 数据流（当前推荐）

```
你 ──飞书──► OpenClaw（cli_a96c20180038dbde，长连接）
              └── DeepSeek（OpenClaw 自己的 key，在 auth-profiles.json）

你 ──浏览器──► Dify（http://localhost）
              └── 模型用 sk-abaf...（在 Dify 设置里填）
```

## Dify 里怎么填 sk-abaf...

1. 打开 http://localhost
2. **设置 → 模型供应商 → DeepSeek**（或 OpenAI-Compatible）
3. API Key 填：`sk-abaf056a56e745b396f0b7937ea503bb`
4. 在应用 **Feishu Bot** 的工作流里选该模型并 **发布**

## 飞书后台（OpenClaw 机器人）

应用：`cli_a96c20180038dbde`

- 事件订阅：**长连接**（不是 HTTP 回调）
- 权限：IM 发消息等
- 发布并添加机器人

## 若要让「飞书消息走 Dify 回答」

需要 **另一个** 飞书应用 + `start_feishu_dify.ps1` + ngrok，与 OpenClaw **不能** 用同一个 App ID 同时收消息。
