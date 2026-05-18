# -*- coding: utf-8 -*-
"""快麦 ERP 开放平台：签名、Token 刷新、按店铺拉单、字段映射。"""
from __future__ import annotations

import hashlib
import hmac
import json
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

# 会话失效前多少秒触发刷新（默认 3 天）
KM_REFRESH_BEFORE_SEC = int(os.getenv("KM_REFRESH_BEFORE_SEC", str(3 * 86400)))

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


def _write_token_file(data: dict) -> None:
    Path(KM_TOKEN_FILE).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
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
    sess = res.get("session") if isinstance(res.get("session"), dict) else res
    merged = {**tok, **sess, **res}
    access = (
        sess.get("accessToken")
        or sess.get("access_token")
        or res.get("accessToken")
        or tok.get("access_token")
    )
    refresh = (
        sess.get("refreshToken")
        or sess.get("refresh_token")
        or tok.get("refresh_token")
    )
    if access:
        merged["access_token"] = access
    if refresh:
        merged["refresh_token"] = refresh
    exp = sess.get("expiresIn") or res.get("expiresIn")
    if exp is not None:
        merged["expiresIn"] = exp
        try:
            fv = float(exp)
            merged["expires_at"] = fv / 1000.0 if fv > 1e12 else (
                fv if fv > 1e9 else time.time() + fv
            )
        except (TypeError, ValueError):
            pass
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
    timeout: int = 60,
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
                batch = res.get("list") or []
                if not isinstance(batch, list):
                    errors.append({"userId": uid, "msg": "无 list"})
                    break
                for row in batch:
                    if isinstance(row, dict):
                        row.setdefault("_km_userId", str(uid))
                    sid = str(row.get("sid") or row.get("tid") or "")
                    if sid and sid not in seen:
                        seen.add(sid)
                        all_orders.append(row)
                if len(batch) < page_size:
                    break
                page_no += 1
                _time.sleep(0.15)

    return all_orders, errors


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
    src = (trade.get("source") or shop.get("source") or "").strip()
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
        spec = (it.get("sysSkuPropertiesName") or it.get("skuPropertiesName") or "").strip()
        items.append(
            {
                "name": (it.get("sysTitle") or it.get("title") or it.get("shortTitle") or ""),
                "sku": (it.get("sysOuterId") or it.get("outerId") or ""),
                "qty": int(it.get("num") or it.get("quantity") or 0),
                "price": it.get("price") or it.get("payment") or 0,
                "spec": spec,
            }
        )

    sys_status = (trade.get("sysStatus") or trade.get("status") or "").strip()
    created_ms = trade.get("payTime") or trade.get("created") or trade.get("updTime")
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

    so_id = str(trade.get("sid") or trade.get("tid") or "")
    return {
        "so_id": so_id,
        "tid": str(trade.get("tid") or ""),
        "platform": platform,
        "platform_label": platform.upper() if platform == "1688" else platform,
        "order_status": sys_status,
        "status_label": KM_SYS_STATUS_LABEL.get(sys_status, sys_status),
        "created": _ms_to_date_str(created_ms),
        "pay_time": _ms_to_date_str(trade.get("payTime")),
        "total_amount": trade.get("payAmount") or trade.get("payment") or 0,
        "receiver_name": trade.get("receiverName") or trade.get("buyerNick") or "",
        "receiver_mobile": trade.get("receiverMobile") or trade.get("receiverPhone") or "",
        "receiver_address": addr,
        "shop_name": shop_name,
        "items": items,
        "buyer_memo": trade.get("buyerMessage") or "",
        "seller_memo": trade.get("sellerMemo") or trade.get("sellerMessage") or "",
        "km_source": src,
        "km_user_id": uid,
    }


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
    out["notes"] = [
        "使用单店参数 userId（驼峰），禁止 userIds",
        "erp.trade.list.query 不含淘系完整数据",
    ]
    return out
