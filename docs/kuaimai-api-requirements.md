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

## 4. 订单查询（双接口，2026-05 大虾实测）

| 接口 | 方法名 | 覆盖 | 说明 |
|------|--------|------|------|
| 销售出库/全量 | `erp.trade.outstock.simple.query` | **含淘系 tm/tb** | 无需 `userId`，按天分页；样本量可达 2 万+ |
| 订单列表 | `erp.trade.list.query` | 非淘系、非拼多多 | **必须单店 `userId`**，禁止 `userIds` |

本仓库：`km_fetch_trades_outstock()` 拉淘系；`km_fetch_trades()` 按店拉 1688/其他。

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

### 4.2 `erp.trade.list.query`

### 业务参数（必须驼峰）

| 参数 | 说明 |
|------|------|
| `timeType` | `created` / `pay_time` / `consign_time` / `audit_time` / `upd_time` |
| `startTime` / `endTime` | `yyyy-MM-dd HH:mm:ss`，单次跨度建议 ≤1 天 |
| `pageNo` / `pageSize` | 页码；`pageSize` 20–200 |
| `status` | 可选，多个逗号分隔，如 `WAIT_SEND_GOODS,WAIT_AUDIT,...` |
| **`userId`** | **单个店铺编号**（与 `erp.shop.list.query` 返回的 `userId` 一致） |

### 已知坑

| 坑 | 说明 |
|----|------|
| **勿用 `userIds`** | 传逗号多店会 `code=33` 非法店铺编号 |
| **必须用 `userId` 单店** | 拉全店需**按店铺循环**调用 |
| **1688 无需奇门** | `source=1688` 店铺走本接口即可；另可用 `alibaba_orders.py` 直连 1688 开放平台兜底 |
| 淘系 tm/tb | 用 **outstock.simple.query**；勿仅用 list.query |
| 时间跨度 | 超过 1 天易失败或漏单，按天切片 |

### 店铺遍历

先 `erp.shop.list.query`，再对每个 `userId` 单独查订单并合并去重（`sid`）。

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

- `km_token.json` 保存 `access_token`、`refresh_token`、`expires_at`（由 `expiresIn` 写入）  
- 距到期不足 3 天或接口提示会话失效时调用 `open.token.refresh`  
- 刷新成功不改变 token 字符串，仅延长有效期  

## 9. 本仓库实现

| 模块 | 说明 |
|------|------|
| `km_api.py` | HMAC-MD5 签名、`open.token.refresh`、outstock + list 拉单、映射 |
| `alibaba_orders.py` | 1688 开放平台直连（无需奇门） |
| `order_sync.py` | 淘系 outstock + 1688 list + 1688 直连 → 缓存 |
| `scripts/km_fetch_orders.py` | 服务器手动拉单/探测 |
| `scripts/km_probe_orders.py` | 快速探测 |
| `app_cs.py` / `app_production.py` | 后台同步、`POST /api/sync/force` |
| `orders_cache.json` | 实时订单缓存 |

凭证模板：`km_token.json.example` → 复制为 `km_token.json`（勿提交 Git）。
