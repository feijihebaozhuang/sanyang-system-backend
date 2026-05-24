# 小马哥 Hermes · 飞书无反应恢复（213 → 87）

> **现象**：业务迁到 87 后，飞书 @ 小马哥/机器人 **没有回复**。  
> **常见原因**：飞书回调还在 **213:18888**，或 87 未部署 `/api/webhook/feishu`，或 **156 OpenClaw** 网关停了。

---

## 先判断：飞书用的是哪种方式

| 方式 | 飞书后台「事件订阅」 | 跑在哪 | 迁 87 后要做什么 |
|------|----------------------|--------|------------------|
| **A. HTTP 回调** | 「将事件发送至开发者服务器」URL 形如 `http://8.138.10.213:18888/...` | 原 **213** | 改 URL + 87 部署 webhook |
| **B. OpenClaw 长连接** | 「使用长连接接收事件」 | **156** | 重启 156 OpenClaw，**不用**改 87 |
| **C. 本机 Dify 桥接** | HTTP + ngrok | **你电脑** | 与本迁移无关 |

打开 [飞书开放平台](https://open.feishu.cn/app) → 对应 App → **事件与回调** 看是 A 还是 B。

---

## 方案 A：HTTP 回调迁到 87（原 213:18888）

### 第 1 步：87 部署代码 + 重启

SSH **87**：

```bash
cd /www/feijihe/repo
git pull origin main
OLD_HOST=admin@8.138.10.213 bash scripts/ops/restore_feishu_hermes_87.sh
```

或分步：

```bash
./deploy.sh
sudo systemctl restart sanyang-production
curl -s https://feijihe.top/api/webhook/feishu
```

**期望**：JSON 含 `"msg":"feishu-dify webhook"`，**不是 404**。

若仍 404 → `stable/` 里缺 `webhook_routes.py` / `feishu_dify.py`，再跑一遍 `./deploy.sh`。

### 第 2 步：从 213 拷 Hermes 缓存（库存 Excel 用）

```bash
scp -r admin@8.138.10.213:/home/admin/.hermes /home/admin/
chown -R admin:admin /home/admin/.hermes
```

### 第 3 步：`.env` 飞书凭证

编辑 `/www/feijihe/stable/.env`（从 **213 旧 stable/.env** 或飞书后台复制）：

```env
FEISHU_DIFY_ENABLED=true
FEISHU_APP_ID=cli_你的AppId
FEISHU_APP_SECRET=你的Secret
FEISHU_VERIFICATION_TOKEN=
FEISHU_ENCRYPT_KEY=

DIFY_API_BASE=http://你的Dify地址/v1
DIFY_API_KEY=app-xxx
```

保存后：

```bash
sudo systemctl restart sanyang-production
curl -s https://feijihe.top/api/webhook/feishu
```

**期望**：`"enabled": true`

### 第 4 步：改飞书后台 URL（关键）

飞书 App → **事件与回调**：

| 项 | 旧（213） | 新（87） |
|----|-----------|----------|
| 订阅方式 | HTTP 服务器 | 同上 |
| 请求地址 | `http://8.138.10.213:18888/...` | **`https://feijihe.top/api/webhook/feishu`** |
| 事件 | `im.message.receive_v1` | 不变 |

保存并通过 URL 校验 → 飞书发「测试」。

---

## 方案 B：OpenClaw 长连接（156）

业务迁 87 **不影响** 长连接，但若 213 清理时误停了 OpenClaw，或飞书仍指向旧 App，会无回复。

SSH **156**（可先 `ssh -J root@8.166.132.87 root@172.16.0.94`）：

```bash
bash /path/to/repo/scripts/ops/restart_openclaw_feishu_156.sh
```

飞书后台必须是：**使用长连接接收事件**（不要填 213/87 的 HTTP 地址）。

---

## 验收

```bash
# 87 上
bash /www/feijihe/repo/scripts/ops/verify_feishu_hermes.sh
```

飞书里 @ 机器人发：**测试**，应有回复。

---

## 分工小结

| 内容 | 机器 |
|------|------|
| 网站 / 飞书 HTTP webhook | **87** |
| OpenClaw 飞书长连接 | **156** |
| MySQL | **213** |
| `/home/admin/.hermes` 文档缓存 | **87**（从 213 拷） |

213 **不要**再开 18888；飞书 **不要**再指 213。
