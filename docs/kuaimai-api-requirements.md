# 快麦 ERP API 对接需求（客服端 3001 + 生产端 3002）

> 与线上一致路径：`/www/feijihe/stable/docs/kuaimai-api-requirements.md`

## 1. 环境与凭证

| 项 | 值 |
|----|-----|
| API 地址 | `https://gw.superboss.cc/router` |
| 请求方式 | `POST`，`Content-Type: application/x-www-form-urlencoded;charset=UTF-8` |
| 凭证文件 | 项目根目录 `km_token.json`（勿提交 Git）或环境变量 `KM_APP_KEY` / `KM_APP_SECRET` / `KM_SESSION` |
| Token 刷新 | `open.token.refresh`，参数 `refreshToken`（驼峰） |

## 2. 公共参数（驼峰）

`method`, `appKey`, `timestamp`（`yyyy-MM-dd HH:mm:ss` GMT+8）, `version=1.0`, `sign_method=hmac`, `session`, `sign`

## 3. 签名（HMAC-MD5，默认）

1. 除 `sign`、值为 `null`、byte[] 外，所有参数按参数名 ASCII 排序  
2. 拼接：`key1value1key2value2...`（无分隔符）  
3. `sign = UPPER(hex(hmac_md5(secret, 拼接串)))`

## 4. 订单查询（2026-05 大虾实测）

| 接口 | 方法名 | 覆盖 | 说明 |
|------|--------|------|------|
| 销售出库/全量 | `erp.trade.outstock.simple.query` | **全平台（1688/tm/tb 等）** | 无需 `userId`，按天分页；7 天待发货约 814 条；历史全量可达 2.7 万+ |
| 订单列表 | `erp.trade.list.query` | — | **线上一律不用**（单店 `userId` 实测常 0 条）；`km_api.km_fetch_trades()` 仅保留供探测 |

本仓库：`order_sync.py` 仅 `km_fetch_trades_outstock(..., source_filter=None)`。

### 4.1 `erp.trade.outstock.simple.query`

| 参数 | 必填 | 说明 |
|------|------|------|
| `pageNo` | 是 | 从 1 开始 |
| `pageSize` | 是 | 20–200 |
| `timeType` | 否 | `created` / `pay_time` / `consign_time` / `upd_time` |
| `startTime` / `endTime` | 否 | `yyyy-MM-dd HH:mm:ss`，跨度建议 ≤1 天 |
| `status` | 否 | 订单状态，多个逗号分隔 |
| `tid` / `sid` | 否 | 平台单号 / 系统单号 |

淘系手机号等敏感字段会脱敏（`receiverMobile`）。

### 已知坑

| 坑 | 说明 |
|----|------|
| **勿对 outstock 设 source_filter=tm/tb** | 会漏掉 1688（约 700 条/7 天） |
| **1688 收件人脱敏** | 快麦侧地址可能不完整；可选 `alibaba_orders.py` 直连兜底 |
| **拼多多** | 需另申请方舟接口 |
| 时间跨度 | 超过 1 天易失败或漏单，按天切片（`km_fetch_trades_outstock` 已按天切） |
| `pageSize` | 最小 20，最大 200 |

## 5. 店铺 ID 一览（2026-05 实测）

| userId | source | 简称/备注 |
|--------|--------|-----------|
| 900622681 | tm | 天猫彩色 |
| 900622690 | tm | 天猫正方形 |
| 900622693 | tm | 天猫彩色 |
| 900622697 | tm | 天猫扣底盒 |
| 900622699 | tm | 天猫止合 |
| 900622706 | tb | 淘宝当下家 |
| 900622769 | 1688 | 友尚包装 |
| 900623858 | tb | 俊鑫纸品 |
| 900623866 | tb | 品牌店 |
| 900624354 | 1688 | 亚润包装 |
| 900624383 | 1688 | 亚润包装 |
| 900624409 | 1688 | 新鑫星 |
| 900624423 | 1688 | 正方形 |
| 900624447 | 1688 | 大鱼 |
| 900624458 | open | 线下单 |

## 6. `source` → 系统 `platform`

| source | platform |
|--------|----------|
| 1688 | 1688 |
| tm | tmall |
| tb | taobao |
| jd | jd |
| pdd | pdd |
| sys | sys |
| open | other |

## 7. 店铺名展示

展示用店铺名：去掉前缀 **`飞机盒`**（如 `飞机盒彩色专卖店` → `彩色专卖店`）。  
1688 优先用 `shortTitle` / `shopLabel`。

## 8. Token 自动刷新

- `km_token.json` 保存 `access_token`、`refresh_token`、`expires_at`（accessToken 有效期约 30 天）  
- 距到期不足 **25 天**（`KM_REFRESH_BEFORE_SEC`）或接口提示会话失效时调用 `open.token.refresh`  
- 建议 crontab：`scripts/km_refresh_token_cron.sh`（每月 1 日、26 日凌晨 3 点）  

## 9. 本仓库实现

| 模块 | 说明 |
|------|------|
| `km_api.py` | HMAC-MD5 签名、`open.token.refresh`、outstock 拉单、映射 |
| `alibaba_orders.py` | 1688 开放平台直连（可选兜底） |
| `order_sync.py` | outstock 全平台 + 可选 1688 直连 → 缓存 |
| `scripts/km_fetch_orders.py` | 服务器手动拉单/探测 |
| `scripts/km_probe_orders.py` | 快速探测 |
| `app_cs.py` / `app_production.py` | 后台同步、`POST /api/sync/force` |
| `orders_cache.json` | 实时订单缓存 |

凭证模板：`km_token.json.example` → 复制为 `km_token.json`（勿提交 Git）。
