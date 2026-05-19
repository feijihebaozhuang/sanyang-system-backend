# -*- coding: utf-8 -*-
"""快麦 ERP 开放平台：签名、Token 刷新、按店铺拉单、字段映射。"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import operator
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

_ROOT = Path(__file__).resolve().parent
KM_TOKEN_FILE = os.getenv("KM_TOKEN_FILE", str(_ROOT / "km_token.json")).strip()
KM_API_URL = os.getenv("KM_API_URL", "https://gw.superboss.cc/router").strip()
KM_APP_KEY = os.getenv("KM_APP_KEY", "").strip()
KM_APP_SECRET = os.getenv("KM_APP_SECRET", "").strip()
KM_SESSION = os.getenv("KM_SESSION", "").strip()

# 会话失效前多少秒触发刷新（默认 25 天；accessToken 有效期 30 天）
KM_REFRESH_BEFORE_SEC = int(os.getenv("KM_REFRESH_BEFORE_SEC", str(25 * 86400)))

# 淘系 source（仅用于统计/筛选；拉单统一走 outstock.simple.query）
KM_TM_TB_SOURCES = frozenset({"tm", "tb"})

KM_SOURCE_PLATFORM = {
    "1688": "1688",
    "tm": "tmall",
    "tb": "taobao",
    "jd": "jd",
    "pdd": "pdd",
    "sys": "sys",
    "open": "other",
}

KM_SYS_STATUS_LABEL = {
    "WAIT_BUYER_PAY": "待付款",
    "WAIT_AUDIT": "待审核",
    "WAIT_FINANCE_AUDIT": "待财审",
    "FINISHED_AUDIT": "审核完成",
    "WAIT_EXPRESS_PRINT": "待打印",
    "WAIT_PACKAGE": "待打包",
    "WAIT_WEIGHT": "待称重",
    "WAIT_SEND_GOODS": "待发货",
    "WAIT_DEST_SEND_GOODS": "待供销发货",
    "SELLER_SEND_GOODS": "已发货",
    "FINISHED": "已完成",
    "CLOSED": "已关闭",
}

KM_PENDING_STATUSES = (
    "WAIT_SEND_GOODS,WAIT_AUDIT,WAIT_PACKAGE,WAIT_WEIGHT,"
    "WAIT_EXPRESS_PRINT,WAIT_DEST_SEND_GOODS,FINISHED_AUDIT"
)

SESSION_EXPIRED_HINTS = ("会话", "session", "token", "过期", "失效", "授权")

_shop_cache: dict[str, dict] = {}


def _read_token_file() -> dict:
    p = Path(KM_TOKEN_FILE)
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


# 刷新 token 时须保留（勿被 API 响应覆盖）
_TOKEN_CREDENTIAL_KEYS = (
    "app_key",
    "app_secret",
    "appKey",
    "appSecret",
    "note",
)


def _credential_fields(src: dict) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in _TOKEN_CREDENTIAL_KEYS:
        v = src.get(k)
        if v is not None and str(v).strip():
            out[k] = v
    if KM_APP_KEY and not out.get("app_key") and not out.get("appKey"):
        out["app_key"] = KM_APP_KEY
    if KM_APP_SECRET and not out.get("app_secret") and not out.get("appSecret"):
        out["app_secret"] = KM_APP_SECRET
    return out


def _write_token_file(data: dict) -> None:
    prev = _read_token_file()
    out = {**prev, **data}
    out.update(_credential_fields(prev))
    out.update(_credential_fields(data))
    # 去掉误写入的 API 包装字段
    for junk in (
        "success",
        "code",
        "msg",
        "sub_code",
        "sub_msg",
        "request_id",
        "error_response",
    ):
        out.pop(junk, None)
    if isinstance(out.get("session"), dict):
        sess = out.pop("session")
        access = sess.get("accessToken") or sess.get("access_token")
        if access and not out.get("access_token"):
            out["access_token"] = access
        refresh = sess.get("refreshToken") or sess.get("refresh_token")
        if refresh and not out.get("refresh_token"):
            out["refresh_token"] = refresh
    Path(KM_TOKEN_FILE).write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def km_session() -> str:
    if KM_SESSION:
        return KM_SESSION
    tok = _read_token_file()
    return (
        tok.get("access_token") or tok.get("accessToken") or tok.get("session") or ""
    ).strip()


def km_app_key() -> str:
    tok = _read_token_file()
    return (KM_APP_KEY or tok.get("app_key") or tok.get("appKey") or "").strip()


def km_app_secret() -> str:
    tok = _read_token_file()
    return (KM_APP_SECRET or tok.get("app_secret") or tok.get("appSecret") or "").strip()


def km_configured() -> bool:
    return bool(km_app_key() and km_app_secret() and km_session())


def _expires_at_from_token(tok: dict) -> float:
    """统一为 Unix 秒。"""
    v = tok.get("expires_at") or tok.get("expiresAt")
    if v is not None:
        try:
            fv = float(v)
            if fv > 1e12:
                return fv / 1000.0
            return fv
        except (TypeError, ValueError):
            pass
    exp_in = tok.get("expiresIn") or tok.get("expires_in")
    if exp_in is not None:
        try:
            fv = float(exp_in)
            if fv > 1e12:
                return fv / 1000.0
            if fv > 1e9:
                return fv
            return time.time() + fv
        except (TypeError, ValueError):
            pass
    return 0.0


def _merge_refresh_into_token(tok: dict, res: dict) -> dict:
    """仅合并 token 字段，禁止把整段 API 响应写入 km_token.json。"""
    merged = dict(tok)
    sess = res.get("session") if isinstance(res.get("session"), dict) else {}
    for src in (sess, res):
        if not isinstance(src, dict):
            continue
        access = src.get("accessToken") or src.get("access_token")
        refresh = src.get("refreshToken") or src.get("refresh_token")
        if access:
            merged["access_token"] = access
        if refresh:
            merged["refresh_token"] = refresh
        exp = src.get("expiresIn") or src.get("expires_in")
        if exp is not None:
            merged["expiresIn"] = exp
            try:
                fv = float(exp)
                merged["expires_at"] = (
                    fv / 1000.0
                    if fv > 1e12
                    else (fv if fv > 1e9 else time.time() + fv)
                )
            except (TypeError, ValueError):
                pass
    merged.update(_credential_fields(tok))
    merged["refreshed_at"] = time.time()
    return merged


def km_refresh_token() -> dict[str, Any]:
    tok = _read_token_file()
    refresh = (tok.get("refresh_token") or tok.get("refreshToken") or "").strip()
    if not refresh:
        return {"success": False, "msg": "km_token.json 缺少 refresh_token"}
    res = km_request("open.token.refresh", {"refreshToken": refresh}, _skip_ensure=True)
    if res.get("success"):
        _write_token_file(_merge_refresh_into_token(tok, res))
    return res


def km_ensure_session(*, force: bool = False) -> bool:
    """到期前自动刷新；无 refresh_token 时仅依赖现有 session。"""
    if not km_configured() and not (km_app_key() and km_app_secret()):
        return False
    tok = _read_token_file()
    refresh = (tok.get("refresh_token") or tok.get("refreshToken") or "").strip()
    if not refresh:
        return bool(km_session())
    exp_at = _expires_at_from_token(tok)
    if force or not exp_at or exp_at - time.time() < KM_REFRESH_BEFORE_SEC:
        r = km_refresh_token()
        return bool(r.get("success"))
    return True


def km_sign(params: dict[str, Any], secret: str, sign_method: str = "hmac") -> str:
    clean = {k: v for k, v in params.items() if v is not None and k != "sign"}
    parts = "".join(f"{k}{clean[k]}" for k, _ in sorted(clean.items(), key=operator.itemgetter(0)))
    if sign_method == "md5":
        return hashlib.md5((secret + parts + secret).encode("utf-8")).hexdigest().upper()
    if sign_method == "hmac-sha256":
        return (
            hmac.new(secret.encode("utf-8"), parts.encode("utf-8"), hashlib.sha256)
            .hexdigest()
            .upper()
        )
    return (
        hmac.new(secret.encode("utf-8"), parts.encode("utf-8"), hashlib.md5)
        .hexdigest()
        .upper()
    )


def _is_session_error(res: dict) -> bool:
    if not res or res.get("success"):
        return False
    msg = str(res.get("msg") or res.get("message") or "").lower()
    code = str(res.get("code") or "")
    if code in ("27", "26", "40"):
        return True
    return any(h in msg for h in SESSION_EXPIRED_HINTS)


def km_request(
    method: str,
    biz: dict[str, Any] | None = None,
    *,
    session: str | None = None,
    sign_method: str = "hmac",
    timeout: int | None = None,
    _skip_ensure: bool = False,
    _retry: bool = True,
) -> dict[str, Any]:
    if not _skip_ensure:
        km_ensure_session()

    app_key = km_app_key()
    app_secret = km_app_secret()
    session = (session or km_session()).strip()
    if not app_key or not app_secret or not session:
        return {
            "success": False,
            "code": "local",
            "msg": "缺少快麦配置：KM_APP_KEY / KM_APP_SECRET / KM_SESSION 或 km_token.json",
        }

    biz = dict(biz or {})
    if "userIds" in biz:
        del biz["userIds"]

    params: dict[str, Any] = {
        "method": method,
        "appKey": app_key,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "format": "json",
        "version": "1.0",
        "sign_method": sign_method,
        "session": session,
    }
    params.update(biz)
    params["sign"] = km_sign(params, app_secret, sign_method)

    body = urllib.parse.urlencode(
        {k: str(v) for k, v in params.items() if v is not None}
    ).encode("utf-8")
    req = urllib.request.Request(
        KM_API_URL,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
    )
    if timeout is None:
        timeout = int(os.getenv("KM_REQUEST_TIMEOUT", "120"))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            return {"success": False, "code": str(e.code), "msg": raw[:500]}
    except urllib.error.URLError as e:
        return {"success": False, "code": "network", "msg": str(e.reason)}
    else:
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            return {"success": False, "code": "parse", "msg": raw[:500]}

    if _retry and _is_session_error(result) and not _skip_ensure:
        if km_refresh_token().get("success"):
            return km_request(
                method, biz, session=km_session(), sign_method=sign_method,
                timeout=timeout, _skip_ensure=True, _retry=False,
            )
    return result


def km_normalize_shop_name(name: str) -> str:
    """展示用店铺名：去掉「飞机盒」前缀。"""
    s = (name or "").strip()
    if s.startswith("飞机盒"):
        s = s[3:].strip()
    return s


def km_platform_from_source(source: str) -> str:
    return KM_SOURCE_PLATFORM.get((source or "").strip(), (source or "other"))


def km_resolve_raw_source(trade: dict, shop: dict | None = None) -> str:
    """快麦原始渠道码：tm / tb / 1688 / jd / …"""
    shop = shop or {}
    for key in (
        "source",
        "tradeSource",
        "shopSource",
        "platformSource",
        "platformCode",
        "platform",
    ):
        v = trade.get(key)
        if v is not None and str(v).strip():
            raw = str(v).strip().lower()
            if raw in ("tmall", "天猫"):
                return "tm"
            if raw in ("taobao", "淘宝"):
                return "tb"
            if raw in KM_SOURCE_PLATFORM or raw in ("1688", "tm", "tb", "jd", "pdd", "sys", "open"):
                return raw
    if shop.get("source"):
        return str(shop["source"]).strip()
    title = (
        (trade.get("shopName") or trade.get("shopLabel") or trade.get("shortTitle") or "")
    ).lower()
    if "1688" in title:
        return "1688"
    if "天猫" in title or "tmall" in title:
        return "tm"
    if "淘宝" in title or "taobao" in title:
        return "tb"
    return ""


def km_resolve_sys_status(trade: dict) -> str:
    for key in ("sysStatus", "sys_status", "status", "orderStatus", "tradeStatus"):
        v = trade.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def km_resolve_internal_so_id(trade: dict) -> str:
    """快麦 ERP 内部单号（sid），勿用平台 tid 作为 so_id。"""
    tid = str(trade.get("tid") or "").strip()
    candidates: list[str] = []
    for key in ("sid", "tradeId", "trade_id", "shortId", "id"):
        v = trade.get(key)
        if v is None:
            continue
        s = str(v).strip()
        if not s:
            continue
        if tid and s == tid and len(tid) > 14:
            continue
        candidates.append(s)
    if tid and len(tid) > 14:
        short = [c for c in candidates if c != tid and len(c) <= 14]
        if short:
            return short[0]
    for key in ("sid", "tradeId", "trade_id", "shortId"):
        v = trade.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    sid = str(trade.get("sid") or "").strip()
    return sid


def km_normalize_so_id_fields(o: dict) -> None:
    """旧缓存可能把平台 tid 写在 so_id，读取时尽量纠正为内部单号。"""
    tid = str(o.get("tid") or o.get("platform_tid") or "").strip()
    sid = str(o.get("km_sid") or o.get("sid") or "").strip()
    so = str(o.get("so_id") or "").strip()
    if sid:
        o["km_sid"] = sid
        if not so or (tid and so == tid) or len(so) > 14:
            o["so_id"] = sid
    elif so and len(so) <= 14:
        o["km_sid"] = so
    elif tid and so == tid and len(so) > 14:
        o["platform_tid"] = tid


def km_to_float(val: Any, default: float = 0.0) -> float:
    """快麦金额字段常为字符串（如 '360.00'），统一转 float 供前端 toFixed。"""
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def finalize_cache_order(o: dict) -> dict:
    """写入 orders_cache 前统一 source / status / platform（页面与筛选依赖）。"""
    src = (o.get("source") or o.get("km_source") or "").strip()
    if not src:
        plat = (o.get("platform") or "").strip()
        plat_to_src = {
            "tmall": "tm",
            "taobao": "tb",
            "1688": "1688",
            "jd": "jd",
            "pdd": "pdd",
            "sys": "sys",
            "other": "open",
        }
        src = plat_to_src.get(plat, plat or "open")
    o["source"] = src
    o["km_source"] = src

    sys_status = (o.get("order_status") or "").strip()
    label = (o.get("status_label") or "").strip()
    if not label:
        label = KM_SYS_STATUS_LABEL.get(sys_status, sys_status) if sys_status else ""
    if not label:
        label = "待发货" if src == "1688" else "待处理"
    o["status_label"] = label
    o["status"] = label

    if not o.get("platform"):
        o["platform"] = km_platform_from_source(src) if src else "other"
    plat = o["platform"]
    o["platform_label"] = (
        "1688"
        if plat == "1688"
        else {"tmall": "天猫", "taobao": "淘宝"}.get(plat, plat)
    )
    o["total_amount"] = km_to_float(o.get("total_amount"))
    if o.get("shipping_fee") is not None:
        o["shipping_fee"] = km_to_float(o.get("shipping_fee"))
    for it in o.get("items") or []:
        if not isinstance(it, dict):
            continue
        if it.get("price") is not None:
            it["price"] = km_to_float(it.get("price"))
        merged = km_item_for_resolve(it)
        display = km_resolve_item_display(it)
        if display:
            it["spec"] = display
            it["display"] = display
            it["platform_attrs"] = display
        elif not (it.get("display") or "").strip():
            it["display"] = (it.get("spec") or "").strip()
        it["is_customization"] = km_item_is_customization(merged)
    km_normalize_so_id_fields(o)
    km_enrich_receiver_region(o)
    return o


def km_enrich_receiver_region(o: dict) -> dict:
    """补全省/市（旧缓存或仅有拼接地址时）。"""
    p = (o.get("receiver_province") or "").strip()
    c = (o.get("receiver_city") or "").strip()
    if p and c:
        return o
    addr = (o.get("receiver_address") or "").strip()
    if not p and addr:
        m = re.match(r"^(.{2,12}?(?:省|自治区|特别行政区))", addr)
        if m:
            p = m.group(1)
    if not c and addr:
        rest = addr[len(p) :] if p else addr
        m2 = re.match(r"^(.{2,12}?(?:市|自治州|地区|盟))", rest)
        if m2:
            c = m2.group(1)
    if p:
        o["receiver_province"] = p
    if c:
        o["receiver_city"] = c
    return o


def km_shop_lookup(*, refresh: bool = False) -> dict[str, dict]:
    global _shop_cache
    if _shop_cache and not refresh:
        return _shop_cache
    res = km_request("erp.shop.list.query", {})
    out: dict[str, dict] = {}
    if not res.get("success"):
        return out
    for s in res.get("list") or []:
        if not isinstance(s, dict):
            continue
        uid = str(s.get("userId") or "")
        if not uid:
            continue
        src = (s.get("source") or "").strip()
        platform = km_platform_from_source(src)
        short = (s.get("shortTitle") or s.get("shopLabel") or "").strip()
        title = (s.get("title") or s.get("nick") or short).strip()
        raw_name = short or title
        out[uid] = {
            "userId": uid,
            "shopId": str(s.get("shopId") or ""),
            "source": src,
            "platform": platform,
            "title": title,
            "shortTitle": short,
            "shop_name": km_normalize_shop_name(raw_name),
            "shop_name_raw": raw_name,
        }
    _shop_cache = out
    return out


def km_shop_list(*, refresh: bool = False) -> list[dict]:
    return list(km_shop_lookup(refresh=refresh).values())


def _response_trade_list(res: dict[str, Any]) -> list:
    if not res.get("success"):
        return []
    batch = res.get("list")
    if isinstance(batch, list):
        return batch
    data = res.get("data")
    if isinstance(data, dict):
        inner = data.get("list") or data.get("trades") or data.get("orders")
        if isinstance(inner, list):
            return inner
    return []


def km_outstock_simple_page(
    *,
    start_time: str,
    end_time: str,
    page_no: int = 1,
    page_size: int = 200,
    time_type: str = "upd_time",
    status: str | None = None,
    tid: str | None = None,
    sid: str | None = None,
) -> dict[str, Any]:
    """erp.trade.outstock.simple.query — 含淘系/天猫/淘宝，无需按店 userId。"""
    page_size = max(20, min(200, int(page_size)))
    biz: dict[str, Any] = {
        "timeType": time_type,
        "startTime": start_time,
        "endTime": end_time,
        "pageNo": str(page_no),
        "pageSize": str(page_size),
    }
    if status:
        biz["status"] = status
    if tid:
        biz["tid"] = str(tid)
    if sid:
        biz["sid"] = str(sid)
    return km_request("erp.trade.outstock.simple.query", biz)


def km_fetch_trades_outstock(
    days_back: int = 14,
    *,
    time_type: str = "upd_time",
    status: str | None = KM_PENDING_STATUSES,
    page_size: int = 200,
    source_filter: frozenset[str] | None = KM_TM_TB_SOURCES,
) -> tuple[list[dict], list[dict]]:
    """按天分页拉取出库/订单（淘系等）；source_filter 为 None 时不按 source 过滤。"""
    end = datetime.now()
    start = end - timedelta(days=max(1, days_back))
    all_orders: list[dict] = []
    errors: list[dict] = []
    seen: set[str] = set()

    import time as _time

    for start_time, end_time in _day_ranges(start, end):
        page_no = 1
        while page_no <= 500:
            res = km_outstock_simple_page(
                start_time=start_time,
                end_time=end_time,
                page_no=page_no,
                page_size=page_size,
                time_type=time_type,
                status=status,
            )
            if not res.get("success"):
                errors.append(
                    {
                        "api": "erp.trade.outstock.simple.query",
                        "window": f"{start_time} ~ {end_time}",
                        "page": page_no,
                        "code": res.get("code"),
                        "msg": res.get("msg"),
                    }
                )
                break
            batch = _response_trade_list(res)
            for row in batch:
                if not isinstance(row, dict):
                    continue
                src = (row.get("source") or "").strip()
                if source_filter is not None and src not in source_filter:
                    continue
                sid = km_resolve_internal_so_id(row)
                if sid and sid not in seen:
                    seen.add(sid)
                    uid = str(row.get("userId") or row.get("shopId") or "")
                    if uid:
                        row.setdefault("_km_userId", uid)
                    all_orders.append(row)
            if len(batch) < page_size:
                break
            page_no += 1
            _time.sleep(0.15)

    return all_orders, errors


def km_trade_list_page(
    *,
    start_time: str,
    end_time: str,
    page_no: int = 1,
    page_size: int = 200,
    time_type: str = "pay_time",
    status: str | None = KM_PENDING_STATUSES,
    user_id: str | None = None,
) -> dict[str, Any]:
    """erp.trade.list.query — 单店 userId，驼峰参数。"""
    page_size = max(20, min(200, int(page_size)))
    biz: dict[str, Any] = {
        "timeType": time_type,
        "startTime": start_time,
        "endTime": end_time,
        "pageNo": str(page_no),
        "pageSize": str(page_size),
    }
    if status:
        biz["status"] = status
    if user_id:
        biz["userId"] = str(user_id)
    return km_request("erp.trade.list.query", biz)


def _day_ranges(start: datetime, end: datetime) -> Iterator[tuple[str, str]]:
    cur = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end_day = end.replace(hour=0, minute=0, second=0, microsecond=0)
    while cur <= end_day:
        day_end = cur.replace(hour=23, minute=59, second=59)
        if day_end > end:
            day_end = end
        yield (
            cur.strftime("%Y-%m-%d %H:%M:%S"),
            day_end.strftime("%Y-%m-%d %H:%M:%S"),
        )
        cur += timedelta(days=1)


def km_fetch_trades(
    days_back: int = 14,
    *,
    time_type: str = "pay_time",
    status: str | None = KM_PENDING_STATUSES,
    page_size: int = 200,
    shop_user_ids: list[str] | None = None,
) -> tuple[list[dict], list[dict]]:
    """按店铺 userId 循环 + 按天分页拉单。"""
    shops = km_shop_lookup(refresh=True)
    ids = shop_user_ids or list(shops.keys())
    if not ids:
        return [], [{"msg": "无店铺 userId"}]

    end = datetime.now()
    start = end - timedelta(days=max(1, days_back))
    all_orders: list[dict] = []
    errors: list[dict] = []
    seen: set[str] = set()

    import time as _time

    for uid in ids:
        shop = shops.get(str(uid), {})
        for start_time, end_time in _day_ranges(start, end):
            page_no = 1
            while page_no <= 500:
                res = km_trade_list_page(
                    start_time=start_time,
                    end_time=end_time,
                    page_no=page_no,
                    page_size=page_size,
                    time_type=time_type,
                    status=status,
                    user_id=str(uid),
                )
                if not res.get("success"):
                    errors.append(
                        {
                            "userId": uid,
                            "shop": shop.get("shop_name"),
                            "window": f"{start_time} ~ {end_time}",
                            "page": page_no,
                            "code": res.get("code"),
                            "msg": res.get("msg"),
                        }
                    )
                    break
                batch = _response_trade_list(res)
                if not batch:
                    break
                for row in batch:
                    if isinstance(row, dict):
                        row.setdefault("_km_userId", str(uid))
                    sid = km_resolve_internal_so_id(row)
                    if sid and sid not in seen:
                        seen.add(sid)
                        all_orders.append(row)
                if len(batch) < page_size:
                    break
                page_no += 1
                _time.sleep(0.15)

    return all_orders, errors


def _norm_spec_text(val: Any) -> str:
    if val is None:
        return ""
    return re.sub(r"\s+", " ", str(val).strip())


# 非 SKU 规格字段（orderExt / 平台扩展里常见，勿拼进展示）
_SKIP_SPEC_KEYS = frozenset(
    {
        "customization",
        "promiseaccepttime",
        "promisefinishtime",
        "tid",
        "sid",
        "oid",
        "soid",
        "userid",
        "tradeid",
        "itemid",
        "skuid",
        "numiid",
        "refundingcnt",
        "refundedcnt",
        "skucnt",
        "orderid",
        "companyid",
        "warehouseid",
    }
)

_SKU_SPEC_FIELD_KEYS = (
    "sysSkuPropertiesName",
    "skuPropertiesName",
    "sysSkuPropertiesAlias",
)


def _norm_spec_seg_key(seg: str) -> str:
    return re.sub(r"\s+", "", (seg or "").lower())


def _is_junk_spec_segment(seg: str) -> bool:
    t = _norm_spec_text(seg)
    if not t or len(t) > 120:
        return True
    low = t.lower()
    if '{"' in t or t.startswith("{") or t.startswith("["):
        return True
    if re.fullmatch(r"\d{10,}", t):
        return True
    if re.match(r"^[a-z_]+:\d{10,}", low):
        return True
    head = low.split(":", 1)[0].strip()
    if head in _SKIP_SPEC_KEYS:
        return True
    return False


# 商品编码/标题式 SKU 文案（非下单尺寸）
_SKIP_ATTR_LABELS = frozenset(
    {
        "商品编码",
        "货号",
        "商家编码",
        "商品货号",
        "单品货号",
        "sku编码",
        "sku",
        "款号",
        "条形码",
        "商品名称",
        "产品名称",
        "标题",
    }
)

# 1688/天猫商品页长标题（非买家下单尺寸）
_LISTING_TITLE_HINTS = (
    "批发",
    "现货",
    "瓦楞",
    "包装盒",
    "快递纸箱",
    "丝印",
    "服饰",
    "内衣",
    "饰品",
    "定制链接",
    "飞机盒",
    "纸盒",
    "大市场",
)

_ORDER_SPEC_HINT = re.compile(
    r"长|宽|高|厚|深|尺寸|规格|直径|颜色|材质|材料|硬度|每层|层数|×|[xX]|【[^】]*\d"
)

# 天猫/淘宝/1688 常见尺寸片段（从整段规格或标题里抠出）
_DIM_SNIPPET_PATTERNS = (
    re.compile(r"长\s*x?\s*宽\s*【[^】]+】", re.I),
    re.compile(r"高度?\s*【[^】]+】", re.I),
    re.compile(r"(?:外|内)?尺寸\s*[:：]?\s*[^;；]+", re.I),
    re.compile(
        r"\d+\.?\d*\s*(?:cm|CM|毫米|mm|厘米)?\s*[*×xX]\s*\d+\.?\d*"
        r"(?:\s*(?:cm|CM|毫米|mm|厘米)?\s*[*×xX]\s*\d+\.?\d*)?",
        re.I,
    ),
    re.compile(r"(?:宽|长)度?\s*\d+\.?\d*\s*(?:cm|CM|厘米)?", re.I),
    re.compile(r"高\s*度?\s*\d+\.?\d*\s*(?:cm|CM|厘米)?", re.I),
)


def _is_product_listing_title(text: str) -> bool:
    """店铺商品长标题，不是买家选的 SKU 规格（1688 定制链接常见）。"""
    t = _norm_spec_text(text)
    if not t or len(t) < 18:
        return False
    if re.search(r"长\s*x?\s*宽|高度?\s*【", t, re.I):
        return False
    if re.search(
        r"\d+\.?\d*\s*(?:cm|CM|厘米|mm)?\s*[*×xX]\s*\d+\.?\d*", t, re.I
    ):
        return False
    hits = sum(1 for h in _LISTING_TITLE_HINTS if h in t)
    return hits >= 2 or (len(t) >= 32 and hits >= 1)


def _is_product_code_segment(seg: str) -> bool:
    """如 10厘米-27厘米-正方形【零售】 等货号/标题，不是订单尺寸属性。"""
    t = _norm_spec_text(seg)
    if not t:
        return False
    if _is_product_listing_title(t):
        return True
    if re.search(r"【(?:零售|批发|现货|包邮|定制链接)", t):
        return True
    head = t.split(":", 1)[0].strip() if ":" in t else ""
    if head in _SKIP_ATTR_LABELS or head.lower() in _SKIP_ATTR_LABELS:
        return True
    # 厘米区间+形状名，且无长宽高等尺寸描述
    if re.search(r"\d+厘米\s*-\s*\d+厘米", t) and not re.search(
        r"长\s*[x×X]|长x宽|宽度|高度|高【", t
    ):
        return True
    return False


def _is_dimension_only_segment(seg: str) -> bool:
    """纯数字尺寸如 14*10*7、宽度14CM高度7CM。"""
    if _is_junk_spec_segment(seg) or _is_product_code_segment(seg):
        return False
    t = _norm_spec_text(seg)
    if re.search(
        r"\d+\.?\d*\s*(?:cm|CM|毫米|mm|厘米)?\s*[*×xX]\s*\d+\.?\d*", t, re.I
    ):
        return True
    if re.search(r"[长宽]\s*[*×xX]?\s*\d", t):
        return True
    if re.search(r"高\s*度?\s*【?\s*\d", t, re.I):
        return True
    return False


def _is_order_spec_segment(seg: str) -> bool:
    """客服/production 需要的下单属性：长宽高、材质颜色等。"""
    if _is_junk_spec_segment(seg) or _is_product_code_segment(seg):
        return False
    if _is_dimension_only_segment(seg):
        return True
    if ":" in seg or "：" in seg:
        key, _, val = seg.partition(":") if ":" in seg else seg.partition("：")
        if _ORDER_SPEC_HINT.search((key or "") + (val or "")):
            return True
    val = seg.rsplit(":", 1)[-1].strip() if (":" in seg or "：" in seg) else seg
    return bool(_ORDER_SPEC_HINT.search(val))


def _extract_dimension_snippets(text: str) -> list[str]:
    if not text:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for pat in _DIM_SNIPPET_PATTERNS:
        for m in pat.finditer(text):
            s = _norm_spec_text(m.group(0))
            if not s or s in seen:
                continue
            if _is_junk_spec_segment(s) or _is_product_code_segment(s):
                continue
            seen.add(s)
            found.append(s)
    return found


def _split_property_blob(text: str) -> list[str]:
    """拆分天猫/淘宝规格串：; 分隔，以及同一串里多个【…】属性。"""
    t = _norm_spec_text(text)
    if not t:
        return []
    chunks: list[str] = []
    for part in re.split(r"[;；]+", t.replace("：", ":")):
        part = part.strip()
        if not part:
            continue
        if part.count("【") >= 2:
            subs = re.findall(r"[^;；\s]*【[^】]+】[^;；\s]*", part)
            if subs:
                chunks.extend(s.strip() for s in subs if s.strip())
                rest = re.sub(r"[^;；\s]*【[^】]+】[^;；\s]*", " ", part).strip()
                if rest and not rest.isspace():
                    chunks.append(rest)
                continue
        chunks.append(part)
    return chunks


def _spec_parts_add_from_blob(parts: list[str], seen: set[str], text: str) -> None:
    if not text:
        return
    for seg in _split_property_blob(text):
        if _is_order_spec_segment(seg):
            _spec_parts_add(parts, seen, seg)
    for snip in _extract_dimension_snippets(text):
        _spec_parts_add(parts, seen, snip)


def _parts_have_dimensions(parts: list[str]) -> bool:
    joined = "；".join(parts)
    if re.search(r"\d\s*[*×xX]\s*\d", joined):
        return True
    if re.search(r"[长宽].*\d|高.*\d|【\s*\d", joined):
        return True
    return False


def km_format_dimensions_from_text(text: str, qty: int = 0) -> str:
    """从标题/备注等补全尺寸（天猫 SKU 常只有材质，尺寸在标题里）。"""
    t = _norm_spec_text(text)
    if not t:
        return ""
    labeled = _extract_dimension_snippets(t)
    if labeled:
        return "；".join(labeled)

    fmt = lambda n: str(int(n)) if n == int(n) else str(n)

    m3 = re.search(
        r"(\d+\.?\d*)\s*(?:cm|CM|厘米|mm)?\s*[*×xX]\s*(\d+\.?\d*)\s*(?:cm|CM|厘米|mm)?"
        r"\s*[*×xX]\s*(\d+\.?\d*)",
        t,
        re.I,
    )
    if m3:
        a, b, c = float(m3.group(1)), float(m3.group(2)), float(m3.group(3))
        if abs(c - qty) < 0.01:
            return f"{fmt(a)}×{fmt(b)}"
        return f"{fmt(a)}×{fmt(b)}×{fmt(c)}"

    lw = re.search(
        r"宽度(\d+\.?\d*).*?高度(\d+\.?\d*)|长[度]?(\d+\.?\d*).*?宽[度]?(\d+\.?\d*)",
        t,
        re.I,
    )
    if lw:
        n1 = lw.group(1) or lw.group(3) or ""
        n2 = lw.group(2) or lw.group(4) or ""
        if n1 and n2:
            return f"{fmt(float(n1))}×{fmt(float(n2))}"

    pair = re.search(
        r"(\d+\.?\d*)\s*(?:cm|CM|厘米|mm)?\s*[*×xX]\s*(\d+\.?\d*)", t, re.I
    )
    if pair:
        return f"{fmt(float(pair.group(1)))}×{fmt(float(pair.group(2)))}"

    hm = re.search(r"(?:高(?:度)?[【\[]?|【)(\d+\.?\d*)\s*(?:cm|CM|厘米)?", t, re.I)
    if hm:
        return f"高度【{fmt(float(hm.group(1)))}厘米】"
    return ""


def _split_sku_spec_segments(text: str) -> list[str]:
    if not text:
        return []
    out: list[str] = []
    for seg in re.split(r"[;；]+", text):
        s = _norm_spec_text(seg)
        if s and _is_order_spec_segment(s):
            out.append(s)
    return out


def _spec_value_keys(seg: str) -> set[str]:
    """提取片段中用于去重的值部分（含「名:值」里的值）。"""
    t = _norm_spec_text(seg)
    keys = {_norm_spec_seg_key(t)}
    if ":" in t:
        keys.add(_norm_spec_seg_key(t.rsplit(":", 1)[-1]))
    return {k for k in keys if k}


def _spec_parts_add(parts: list[str], seen: set[str], raw: Any) -> None:
    t = _norm_spec_text(raw)
    if not t or not _is_order_spec_segment(t):
        return
    val_keys = _spec_value_keys(t)
    if val_keys & seen:
        return
    for p in list(parts):
        pk = _norm_spec_seg_key(p)
        for vk in val_keys:
            if pk == vk or (len(vk) > 6 and (vk in pk or pk in vk)):
                return
    parts.append(t)
    seen |= val_keys


def _spec_parts_add_segments(parts: list[str], seen: set[str], text: str) -> None:
    for seg in _split_sku_spec_segments(text):
        _spec_parts_add(parts, seen, seg)


def merge_1688_sku_infos(sku_infos: Any) -> str:
    """1688 productItems.skuInfos → 买家下单属性（原样拼接，仅去掉扩展字段污染）。"""
    if not isinstance(sku_infos, list):
        return ""
    parts: list[str] = []
    seen: set[str] = set()
    for info in sku_infos:
        if not isinstance(info, dict):
            continue
        name = _norm_spec_text(info.get("name") or info.get("attributeName") or "")
        value = _norm_spec_text(info.get("value") or info.get("attributeValue") or "")
        if name and (
            name.lower() in _SKIP_SPEC_KEYS
            or name in _SKIP_ATTR_LABELS
            or name.lower() in _SKIP_ATTR_LABELS
        ):
            continue
        if value and _is_junk_spec_segment(value):
            continue
        if name and value:
            piece = f"{name}:{value}"
        else:
            piece = value or name
        if not piece or _is_junk_spec_segment(piece):
            continue
        key = _norm_spec_seg_key(piece)
        if key in seen:
            continue
        seen.add(key)
        parts.append(piece)
    return "；".join(parts)


def _dedupe_attr_segments(segments: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for seg in segments:
        s = _norm_spec_text(seg)
        if not s or _is_junk_spec_segment(s):
            continue
        k = _norm_spec_seg_key(s)
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
    return out


def _strip_attrs_pollution(text: str) -> str:
    """只去掉 tid/sid/JSON 等污染，保留平台买家可见属性原文。"""
    if not text:
        return ""
    parts: list[str] = []
    for seg in re.split(r"[;；\n]+", text.replace("：", ":")):
        s = _norm_spec_text(seg)
        if s and not _is_junk_spec_segment(s):
            parts.append(s)
    return "；".join(_dedupe_attr_segments(parts))


# 买家要看的片段（不要平台属性名前缀）
_BUYER_DIM_SNIPPET_RE = re.compile(
    r"长\s*x?\s*宽\s*【[^】]+】|高度?\s*【[^】]+】",
    re.I,
)
_BUYER_NUM_DIM_RE = re.compile(
    r"\d+\.?\d*\s*[*×xX]\s*\d+\.?\d*\s*[*×xX]\s*\d+\.?\d*\s*(?:mm|MM|厘米|cm|CM)?",
    re.I,
)
_BUYER_NUM_DIM2_RE = re.compile(
    r"\d+\.?\d*\s*[*×xX]\s*\d+\.?\d*\s*(?:mm|MM|厘米|cm|CM)?",
    re.I,
)
# 仅「定制链接」类商品算定制（不要用外尺寸、加工等误判）
_CUSTOM_LINK_RE = re.compile(r"定制链接", re.I)
_BUYER_MATERIAL_KEY_RE = re.compile(r"颜色|材质|材料|硬度|瓦楞|层次|规格", re.I)
_BUYER_SKIP_NAME_KEY_RE = re.compile(
    r"编码|货号|标题|名称|链接|定制链接|商品|sku|条形码",
    re.I,
)


def _buyer_spec_pieces_from_text(text: str) -> list[str]:
    """从一段文字抽出展示片段（仅值：尺寸数字或特硬/【外尺寸】等）。"""
    t = _norm_spec_text(text)
    if (
        not t
        or _is_junk_spec_segment(t)
        or _is_product_listing_title(t)
        or _is_product_code_segment(t)
    ):
        return []

    found: list[str] = []
    for m in _BUYER_DIM_SNIPPET_RE.finditer(t):
        s = m.group(0).strip()
        if s:
            found.append(s)
    for m in _BUYER_NUM_DIM_RE.finditer(t):
        s = m.group(0).strip()
        if not s or _is_product_code_segment(s):
            continue
        if any(s in f or f in s for f in found):
            continue
        found.append(s)
    for m in _BUYER_NUM_DIM2_RE.finditer(t):
        s = m.group(0).strip()
        if not s or _is_product_code_segment(s):
            continue
        if any(s in f or f in s for f in found):
            continue
        found.append(s)
    if found:
        return found

    if ":" in t or "：" in t:
        key, _, val = t.partition(":") if ":" in t else t.partition("：")
        key, val = key.strip(), val.strip()
        if not val or _is_product_listing_title(val) or _is_junk_spec_segment(val):
            return []
        if _BUYER_SKIP_NAME_KEY_RE.search(key):
            return []
        sub = _buyer_spec_pieces_from_text(val)
        if sub:
            return sub
        # 材质/尺寸/规格：只要值（如 特硬E瓦、210*210*100 mm）
        if len(val) <= 56 and (
            _BUYER_MATERIAL_KEY_RE.search(key)
            or re.search(r"尺寸|长宽高|大小|规格", key, re.I)
            or "【" in val
            or "单个" in val
            or re.search(r"\d\s*[*×xX]\s*\d", val)
        ):
            if not _is_product_listing_title(val) and not _is_product_code_segment(val):
                return [val]
        return []

    if _is_product_listing_title(t):
        return []
    if re.search(r"【|单个|外尺寸|内尺寸", t) and len(t) <= 56:
        return [t]
    if _BUYER_NUM_DIM_RE.search(t):
        return [t]
    if len(t) <= 32 and re.search(
        r"特硬|优质|牛皮|白色|三层|加硬|台湾|超硬|E瓦|瓦楞|瓦", t
    ):
        return [t]
    return []


def _buyer_property_values_only(raw: str) -> str:
    """严格格式化后仍为空时：去掉属性名，仅保留各段值（过滤货号/标题）。"""
    if not raw:
        return ""
    parts: list[str] = []
    seen: set[str] = set()
    for seg in re.split(r"[;；]+", raw):
        t = _norm_spec_text(seg)
        if not t or _is_junk_spec_segment(t):
            continue
        if ":" in t or "：" in t:
            _, _, t = t.partition(":") if ":" in t else t.partition("：")
            t = t.strip()
        if (
            not t
            or _is_product_listing_title(t)
            or _is_product_code_segment(t)
            or _BUYER_SKIP_NAME_KEY_RE.search(t)
        ):
            continue
        k = _norm_spec_seg_key(t)
        if k in seen:
            continue
        seen.add(k)
        parts.append(t)
    return "；".join(parts)


_CUSTOM_JSON_SKIP_KEYS = frozenset(
    {
        "tid",
        "sid",
        "oid",
        "soid",
        "userid",
        "tradeid",
        "itemid",
        "skuid",
        "numiid",
        "orderid",
        "promiseaccepttime",
        "promisefinishtime",
    }
)


def _customization_has_buyer_content(val: Any) -> bool:
    """淘系 customization 常有 tid/sid，不能据此判定制。"""
    if val is None:
        return False
    if isinstance(val, str):
        s = val.strip()
        if not s or s.lower() in ("{}", "[]", "null", "false", "0", "none"):
            return False
        if s.startswith(("{", "[")):
            try:
                val = json.loads(s)
            except json.JSONDecodeError:
                return bool(re.search(r"长|宽|高|厘米|cm|mm|【", s, re.I))
        else:
            return bool(re.search(r"长|宽|高|厘米|cm|mm|【", s, re.I))

    def _walk(obj: Any, depth: int = 0) -> bool:
        if depth > 8:
            return False
        if isinstance(obj, dict):
            for k, v in obj.items():
                kl = str(k).lower()
                if kl in _CUSTOM_JSON_SKIP_KEYS:
                    continue
                if kl in (
                    "text",
                    "content",
                    "customtext",
                    "customization",
                    "buyermsg",
                    "length",
                    "width",
                    "height",
                    "size",
                    "remark",
                ):
                    if v is not None and str(v).strip() not in ("", "{}", "[]"):
                        if re.search(r"\d|长|宽|高|厘米|cm|mm|【", str(v), re.I):
                            return True
                if _walk(v, depth + 1):
                    return True
        elif isinstance(obj, list):
            for x in obj:
                if _walk(x, depth + 1):
                    return True
        elif isinstance(obj, str) and len(obj.strip()) > 2:
            if re.search(r"\d+\s*(?:cm|CM|厘米|mm)|长|宽|高|【", obj, re.I):
                return True
        return False

    if isinstance(val, (dict, list)):
        return _walk(val)
    return False


def _attrs_indicate_custom_product(blob: str) -> bool:
    """买家下单属性里标明定制类（不用商品标题）。"""
    t = _norm_spec_text(blob)
    if not t:
        return False
    if _CUSTOM_LINK_RE.search(t):
        return True
    if re.search(r"来图定制|需定制|支持定制|定制款", t, re.I):
        return True
    if re.search(r"(?:^|[;；\s])定制(?:$|[;；\s、，])", t):
        return True
    return False


def _attrs_have_dimensions(text: str) -> bool:
    """属性里是否已有长宽高（有则按现货规格展示）。"""
    return _display_has_size(text)


def km_item_is_customization(it: dict, *, trade_custom: bool = True) -> bool:
    """
    定制单判定（仅买家下单属性 / customization，不读商品标题）：
    属性含定制类选项或平台 isCustomization，且没有长宽高 → 显示「定制」。
    """
    del trade_custom
    if not isinstance(it, dict):
        return False
    src = km_item_for_resolve(it)
    blob = km_collect_item_raw_attrs(src)
    for field in ("sysSkuRemark", "sysItemRemark"):
        blob = f"{blob} {_norm_spec_text(src.get(field))}".strip()
    extra = _extract_customization_spec_text(src)
    if extra:
        blob = f"{blob} {extra}".strip()
    flagged = src.get("isCustomization") in (True, 1, "1", "true", "True") or src.get(
        "isCustom"
    ) in (True, 1, "1", "true", "True")
    if not flagged and not _attrs_indicate_custom_product(blob) and not extra:
        return False
    return not _attrs_have_dimensions(blob)


def _extract_customization_spec_text(it: dict) -> str:
    """从 customization JSON 抠买家填的尺寸/文字（不展示「定制」二字）。"""
    if not isinstance(it, dict):
        return ""
    chunks: list[str] = []
    for key in (
        "customization",
        "customizationInfo",
        "customInfo",
        "customizationData",
        "buyerCustomization",
    ):
        val = it.get(key)
        if not val:
            continue
        text = _norm_spec_text(val) if isinstance(val, str) else json.dumps(val, ensure_ascii=False)
        if not text:
            continue
        dim = km_format_dimensions_from_text(text, 0)
        if dim:
            chunks.append(dim)
        for m in _BUYER_DIM_SNIPPET_RE.finditer(text):
            chunks.append(m.group(0).strip())
        formatted = km_format_buyer_spec_display(_strip_attrs_pollution(text))
        if formatted:
            chunks.append(formatted)
    return "；".join(_dedupe_attr_segments(chunks))


def _display_has_size(display: str) -> bool:
    t = _norm_spec_text(display)
    if not t:
        return False
    if _BUYER_DIM_SNIPPET_RE.search(t):
        return True
    if _BUYER_NUM_DIM_RE.search(t) or _BUYER_NUM_DIM2_RE.search(t):
        return True
    if re.search(r"长\s*x?\s*宽|高度?\s*【", t, re.I):
        return True
    return False


_KM_ITEM_SNAPSHOT_KEYS = (
    "skuInfos",
    "skuPropertiesName",
    "sysSkuPropertiesName",
    "sysSkuPropertiesAlias",
    "sysSkuRemark",
    "sysItemRemark",
    "customization",
    "customizationInfo",
    "orderExt",
    "sysTitle",
    "title",
    "shortTitle",
    "isCustomization",
    "isCustom",
)


def km_item_snapshot(it: dict) -> dict:
    """同步时保留快麦子单原始字段，便于读缓存后重新解析规格。"""
    if not isinstance(it, dict):
        return {}
    snap: dict[str, Any] = {}
    for key in _KM_ITEM_SNAPSHOT_KEYS:
        val = it.get(key)
        if val is None or val == "":
            continue
        snap[key] = val
    return snap


def km_item_for_resolve(it: dict) -> dict:
    """合并缓存行与 _km 快照，供规格解析使用。"""
    if not isinstance(it, dict):
        return {}
    snap = it.get("_km")
    if isinstance(snap, dict) and snap:
        merged = dict(snap)
        for k, v in it.items():
            if k == "_km" or v in (None, ""):
                continue
            merged[k] = v
        return merged
    return dict(it)


def km_collect_item_raw_attrs(it: dict) -> str:
    """收集平台买家属性原文（未做展示格式化）。"""
    if not isinstance(it, dict):
        return ""
    ali = merge_1688_sku_infos(it.get("skuInfos"))
    if ali:
        return _strip_attrs_pollution(ali)

    plat = _norm_spec_text(it.get("skuPropertiesName"))
    sys = _norm_spec_text(it.get("sysSkuPropertiesName"))
    alias = _norm_spec_text(it.get("sysSkuPropertiesAlias"))
    chunks: list[str] = []
    if plat:
        chunks.extend(_dedupe_attr_segments(re.split(r"[;；]+", plat)))
    if sys and plat != sys:
        for seg in re.split(r"[;；]+", sys):
            s = _norm_spec_text(seg)
            if s and _norm_spec_seg_key(s) not in {_norm_spec_seg_key(c) for c in chunks}:
                chunks.append(s)
    if alias and _norm_spec_seg_key(alias) not in {_norm_spec_seg_key(c) for c in chunks}:
        chunks.append(alias)
    for key in ("sysSkuRemark", "sysItemRemark"):
        remark = _norm_spec_text(it.get(key))
        if remark and not _is_junk_spec_segment(remark):
            rk = _norm_spec_seg_key(remark)
            if rk not in {_norm_spec_seg_key(c) for c in chunks}:
                chunks.append(remark)
    legacy = _norm_spec_text(it.get("spec"))
    if chunks:
        return "；".join(_dedupe_attr_segments(chunks))
    return _strip_attrs_pollution(legacy)


def km_resolve_item_display(it: dict) -> str:
    """
    展示买家选的尺寸与材质。
    仅「定制链接」且整段属性都没有长宽高时，才显示「定制」；有尺寸一律显示尺寸。
    """
    src = km_item_for_resolve(it)
    spec_part = ""
    raw = km_collect_item_raw_attrs(src)
    if raw:
        spec_part = km_format_buyer_spec_display(raw)
        if not spec_part:
            spec_part = _buyer_property_values_only(raw)
    if not spec_part:
        spec_part = _extract_customization_spec_text(src)
    if spec_part:
        return spec_part
    if km_item_is_customization(src):
        return "定制"
    return ""


def km_format_buyer_spec_display(raw: str) -> str:
    """
    客服/生产展示：仅尺寸与选项值。
    例：210*210*100 mm；优质特硬【外尺寸】单个
    不要：材质硬度等级:、尺寸:、10厘米-27厘米-正方形【零售】
    """
    if not raw:
        return ""
    parts: list[str] = []
    seen: set[str] = set()
    for seg in re.split(r"[;；]+", raw):
        for piece in _buyer_spec_pieces_from_text(seg):
            k = _norm_spec_seg_key(piece)
            if k in seen:
                continue
            seen.add(k)
            parts.append(piece)
    return "；".join(parts)


def km_platform_item_attrs(it: dict) -> str:
    """各平台买家下单 SKU 展示（尺寸+材质）。"""
    return km_resolve_item_display(it)


def km_sanitize_spec_text(spec: str) -> str:
    """清理已污染的 spec（去掉 tid/sid/customization 等）。"""
    parts: list[str] = []
    seen: set[str] = set()
    _spec_parts_add_segments(parts, seen, spec or "")
    return "；".join(parts)


def km_merge_line_item_spec(it: dict) -> str:
    """兼容旧名：返回平台买家下单属性原文。"""
    return km_platform_item_attrs(it)


def _ms_to_date_str(ms: Any) -> str:
    try:
        v = int(ms)
        if v > 1_000_000_000_000:
            v //= 1000
        if v <= 0:
            return ""
        return datetime.fromtimestamp(v).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return ""


def km_trade_to_cache_order(trade: dict, shops: dict[str, dict] | None = None) -> dict:
    shops = shops or km_shop_lookup()
    uid = str(
        trade.get("_km_userId") or trade.get("userId") or trade.get("shopId") or ""
    )
    shop = shops.get(uid, {})
    src = km_resolve_raw_source(trade, shop)
    platform = km_platform_from_source(src) if src else shop.get("platform", "other")
    shop_name = km_normalize_shop_name(
        shop.get("shop_name")
        or trade.get("shopName")
        or trade.get("shopLabel")
        or shop.get("shortTitle")
        or ""
    )

    lines = trade.get("orders") or trade.get("orderList") or []
    items = []
    for it in lines:
        if not isinstance(it, dict):
            continue
        qty = int(it.get("num") or it.get("quantity") or 0)
        snap = km_item_snapshot(it)
        item_name = (it.get("sysTitle") or it.get("title") or it.get("shortTitle") or "")
        src = {**snap, "qty": qty}
        display = km_resolve_item_display(src)
        items.append(
            {
                "name": item_name,
                "sku": (it.get("sysOuterId") or it.get("outerId") or ""),
                "qty": qty,
                "price": it.get("price") or it.get("payment") or 0,
                "spec": display,
                "display": display,
                "platform_attrs": display,
                "is_customization": km_item_is_customization(src),
                "_km": snap,
            }
        )

    sys_status = km_resolve_sys_status(trade)
    created_ms = (
        trade.get("payTime")
        or trade.get("created")
        or trade.get("updTime")
        or trade.get("consignTime")
    )
    pay_ms = trade.get("payTime") or created_ms
    addr = "".join(
        filter(
            None,
            [
                trade.get("receiverState"),
                trade.get("receiverCity"),
                trade.get("receiverDistrict"),
                trade.get("receiverAddress"),
            ],
        )
    )

    km_sid = km_resolve_internal_so_id(trade)
    platform_tid = str(trade.get("tid") or "").strip()
    order = {
        "so_id": km_sid or platform_tid,
        "km_sid": km_sid,
        "tid": platform_tid,
        "platform_tid": platform_tid,
        "platform": platform,
        "platform_label": platform.upper() if platform == "1688" else platform,
        "source": src,
        "order_status": sys_status,
        "status_label": KM_SYS_STATUS_LABEL.get(sys_status, sys_status) or sys_status,
        "created": _ms_to_date_str(created_ms),
        "pay_time": _ms_to_date_str(pay_ms),
        "total_amount": km_to_float(
            trade.get("payAmount") or trade.get("payment") or 0
        ),
        "receiver_name": trade.get("receiverName") or trade.get("buyerNick") or "",
        "receiver_mobile": trade.get("receiverMobile") or trade.get("receiverPhone") or "",
        "receiver_province": (trade.get("receiverState") or trade.get("receiverProvince") or "").strip(),
        "receiver_city": (trade.get("receiverCity") or "").strip(),
        "receiver_district": (trade.get("receiverDistrict") or "").strip(),
        "receiver_address": addr,
        "shop_name": shop_name,
        "items": items,
        "buyer_memo": trade.get("buyerMessage") or trade.get("buyerMemo") or "",
        "seller_memo": trade.get("sellerMemo") or trade.get("sellerMessage") or "",
        "km_source": src,
        "km_user_id": uid,
    }
    order["status"] = order["status_label"] or "待处理"
    return finalize_cache_order(order)


def km_probe() -> dict[str, Any]:
    out: dict[str, Any] = {"configured": km_configured()}
    if not out["configured"]:
        out["error"] = "未配置快麦凭证"
        return out
    km_ensure_session()
    tok = _read_token_file()
    out["expires_at"] = _expires_at_from_token(tok)
    t = km_request("open.system.time.get", {}, _skip_ensure=True)
    out["time_get"] = {"success": t.get("success"), "traceId": t.get("traceId")}
    shops = km_shop_list(refresh=True)
    out["shop_count"] = len(shops)
    out["shops"] = [
        {
            "userId": s["userId"],
            "source": s["source"],
            "platform": s["platform"],
            "shop_name": s["shop_name"],
        }
        for s in shops
    ]
    end = datetime.now()
    start = (end - timedelta(days=3)).strftime("%Y-%m-%d 00:00:00")
    end_s = end.strftime("%Y-%m-%d %H:%M:%S")
    per_shop = []
    for s in shops[:3]:
        uid = s["userId"]
        res = km_trade_list_page(
            start_time=start, end_time=end_s, page_no=1, page_size=20,
            time_type="pay_time", status=None, user_id=uid,
        )
        per_shop.append(
            {
                "userId": uid,
                "shop_name": s["shop_name"],
                "success": res.get("success"),
                "count": len(res.get("list") or []),
                "code": res.get("code"),
                "msg": res.get("msg"),
            }
        )
    out["trade_sample_per_shop"] = per_shop
    end_o = end.strftime("%Y-%m-%d %H:%M:%S")
    start_o = (end - timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
    res_o = km_outstock_simple_page(
        start_time=start_o,
        end_time=end_o,
        page_no=1,
        page_size=20,
        time_type="upd_time",
        status=None,
    )
    sample_o = _response_trade_list(res_o)
    sources_o: dict[str, int] = {}
    for row in sample_o[:50]:
        if isinstance(row, dict):
            src = (row.get("source") or "unknown").strip()
            sources_o[src] = sources_o.get(src, 0) + 1
    out["outstock_sample"] = {
        "success": res_o.get("success"),
        "count_page1": len(sample_o),
        "code": res_o.get("code"),
        "msg": res_o.get("msg"),
        "sources_in_sample": sources_o,
    }
    out["notes"] = [
        "待发货：erp.trade.outstock.simple.query（全平台，source_filter=None）",
        "erp.trade.list.query 实测常 0 条，线上一律不用",
        "pageSize 20–200；时间跨度建议 ≤1 天",
        "open.token.refresh 建议每 25 天执行（cron 见 scripts/km_refresh_token_cron.sh）",
    ]
    return out
