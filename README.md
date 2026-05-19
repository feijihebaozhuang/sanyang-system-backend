# 三羊系统

## 分支（仅一套）

| 用途 | 分支 | 端口 |
|------|------|------|
| 代码唯一来源 | `main` | 本地 3001 客服 / 3002 生产 |
| 服务器正式 | `main` → `/www/feijihe/stable` | 3001 / 3002 |

已废弃：`dev` 分支、3003/3004、`deploy.sh dev`。

## 本地开发

```powershell
.\pull-main.ps1
```

- 客服：`python app_cs.py` → http://127.0.0.1:3001
- 生产：`python app_production.py` → http://127.0.0.1:3002

需配置 `.env`（复制 `.env.example`），含 `MYSQL_PASSWORD`、`FLASK_SECRET_KEY`。

## 登录说明

- **系统登录密码**（网页）：默认超级管理员 `admin` / `admin888`（见各 `app_*.py` 内 USERS，可用菜单「修改密码」改）
- **MySQL 密码**：在服务器 `.env` 的 `MYSQL_PASSWORD`，与 `admin888` 无关，不能从代码里猜，需问运维或查服务器 `/www/feijihe/stable/.env`

## 备份锚点

| 版本 | 标签 | 说明 |
|------|------|------|
| **8.33** | `v8.33` | 小马 — 客服 3001 + 生产 3002 双系统完整代码锚点（2026-05-19） |

详见 `docs/ANCHOR-8.33.md`。服务器数据包：`./scripts/backup-anchor.sh 8.33`。

**快麦对齐阶段（只文档、不动业务代码）**：`docs/对齐会议纪要模板.md`、`docs/商家编码映射表.md`。

## 部署（小马哥）

服务器 `/www/feijihe/stable/` 需有（勿提交 Git）：

- `.env` — `MYSQL_PASSWORD`、`FLASK_SECRET_KEY` 等
- `km_token.json` — 快麦 `access_token` / `refresh_token`（可复制 `km_token.json.example`）
- `alibaba_shops.json` — 各 1688 店 `access_token`（保证 1688 一定有单，见 `alibaba_shops.example.json`）

```bash
cd /www/feijihe/repo
git pull origin main
./deploy.sh
```

部署后登录系统，各端执行一次 **`POST /api/sync/force`**（或等后台 5 分钟自动同步）。排错：**`GET /api/km/probe`**。

待发货拉单：快麦 `erp.trade.outstock.simple.query`（全平台，`source_filter=None`）+ 可选 1688 开放平台直连兜底，详见 `docs/kuaimai-api-requirements.md`。
