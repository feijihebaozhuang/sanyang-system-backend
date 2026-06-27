# -*- coding: utf-8 -*-
"""微信小程序鉴权（客户 openid / 客服账号）。"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from settings import FLASK_SECRET_KEY


def _mp_secret() -> str:
    return os.getenv("MP_TOKEN_SECRET", "").strip() or FLASK_SECRET_KEY


def customer_token(openid: str, customer_id: int) -> str:
    raw = f"mp_c:{_mp_secret()}:{openid}:{customer_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def cs_token(username: str, cs_staff_id: int | None) -> str:
    raw = f"mp_cs:{_mp_secret()}:{username}:{cs_staff_id or 0}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def cs_wx_token(openid: str, cs_staff_id: int) -> str:
    raw = f"mp_cs_wx:{_mp_secret()}:{openid}:{cs_staff_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def verify_cs_wx_token(openid: str, cs_staff_id: int, token: str) -> bool:
    if not openid or not cs_staff_id or not token:
        return False
    return token == cs_wx_token(openid, cs_staff_id)


def verify_customer_token(openid: str, customer_id: int, token: str) -> bool:
    if not openid or not customer_id or not token:
        return False
    return token == customer_token(openid, customer_id)


def verify_cs_token(username: str, cs_staff_id: int | None, token: str) -> bool:
    if not username or not token:
        return False
    return token == cs_token(username, cs_staff_id)


def wx_code_to_session(code: str, *, app: str = "customer") -> dict[str, Any]:
    """wx.login code → openid/session_key。

    app=customer → 客户下单小程序（WX_MP_*）
    app=cs       → 报价/客服小程序 quote-weapp（WX_CS_MP_*，缺省回退 WX_MP_*）
    app=scan     → 生产报工小程序 scan-weapp（WX_SCAN_MP_*）
    未配 AppSecret 时开发模式。
    """
    code = (code or "").strip()
    if not code:
        raise ValueError("code 必填")
    if app == "scan":
        appid = os.getenv("WX_SCAN_MP_APPID", "").strip() or "wxf5aa61511c679684"
        secret = os.getenv("WX_SCAN_MP_SECRET", "").strip()
        if not secret:
            raise RuntimeError(
                "未配置生产报工小程序 AppSecret：请在服务器 .env 设置 WX_SCAN_MP_SECRET"
            )
    elif app == "cs":
        appid = os.getenv("WX_CS_MP_APPID", "").strip() or "wxa1d9f876327af0c0"
        secret = os.getenv("WX_CS_MP_SECRET", "").strip()
        cust_appid = os.getenv("WX_MP_APPID", "").strip()
        if not secret and appid == cust_appid:
            secret = os.getenv("WX_MP_SECRET", "").strip()
        if not secret:
            raise RuntimeError(
                "未配置报价小程序 AppSecret：请在 87 服务器 .env 设置 WX_CS_MP_SECRET"
            )
    else:
        appid = os.getenv("WX_MP_APPID", "").strip()
        secret = os.getenv("WX_MP_SECRET", "").strip()
    if not appid or not secret:
        oid = f"dev_{app}_{hashlib.sha256(code.encode()).hexdigest()[:20]}"
        return {"openid": oid, "session_key": "", "dev_mode": True, "app": app}
    url = (
        "https://api.weixin.qq.com/sns/jscode2session"
        f"?appid={urllib.parse.quote(appid)}"
        f"&secret={urllib.parse.quote(secret)}"
        f"&js_code={urllib.parse.quote(code)}"
        "&grant_type=authorization_code"
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(f"微信登录失败: {e}") from e
    if data.get("errcode"):
        raise RuntimeError(data.get("errmsg") or f"微信 errcode {data.get('errcode')}")
    openid = (data.get("openid") or "").strip()
    if not openid:
        raise RuntimeError("微信未返回 openid")
    return {
        "openid": openid,
        "session_key": data.get("session_key") or "",
        "unionid": data.get("unionid") or "",
        "dev_mode": False,
    }


QUOTE_WEAPP_ROLES = frozenset({"客服", "超级管理员"})


def user_can_use_scan_weapp(user: dict | None) -> bool:
    """生产报工小程序：已启用的登录账号均可使用（含员工）。"""
    if not user:
        return False
    if not user.get("enabled", 1):
        return False
    return True


def user_can_use_quote_weapp(user: dict | None) -> bool:
    if not user:
        return False
    if not user.get("enabled", 1):
        return False
    return (user.get("role") or "").strip() in QUOTE_WEAPP_ROLES


def _load_user_row(username: str) -> dict | None:
    import pymysql
    from settings import get_db_config

    username = (username or "").strip()
    if not username:
        return None
    cfg = dict(get_db_config())
    db = pymysql.connect(**cfg, cursorclass=pymysql.cursors.DictCursor)
    try:
        cur = db.cursor()
        cur.execute(
            "SELECT username, password, display_name, role, employee_name, enabled "
            "FROM users WHERE username=%s LIMIT 1",
            (username,),
        )
        return cur.fetchone()
    finally:
        db.close()


def find_user_by_username(username: str) -> dict | None:
    row = _load_user_row(username)
    if not row or not row.get("enabled", 1):
        return None
    return dict(row)


def find_user_by_employee_name(name: str) -> dict | None:
    import pymysql
    from settings import get_db_config

    name = (name or "").strip()
    if not name:
        return None
    cfg = dict(get_db_config())
    db = pymysql.connect(**cfg, cursorclass=pymysql.cursors.DictCursor)
    try:
        cur = db.cursor()
        cur.execute(
            "SELECT username, password, display_name, role, employee_name, enabled "
            "FROM users WHERE enabled=1 AND (employee_name=%s OR display_name=%s OR username=%s)",
            (name, name, name),
        )
        rows = list(cur.fetchall() or [])
    finally:
        db.close()
    for row in rows:
        if user_can_use_quote_weapp(row):
            return dict(row)
    return dict(rows[0]) if rows else None


def verify_user_password(username: str, password: str) -> dict | None:
    username = (username or "").strip()
    if not username or not password:
        return None
    row = _load_user_row(username)
    if not row or not row.get("enabled", 1):
        return None
    from password_utils import verify_password
    if not verify_password(password, row.get("password") or ""):
        return None
    return dict(row)


def verify_quote_weapp_password(username: str, password: str) -> tuple[dict | None, str]:
    """返回 (user, error)。error 非空表示密码对但角色不允许等。"""
    user = verify_user_password(username, password)
    if not user:
        return None, "账号或密码错误"
    if not user_can_use_quote_weapp(user):
        return None, "仅客服和超级管理员可使用报价小程序"
    return user, ""


def verify_cs_password(username: str, password: str) -> dict | None:
    """校验 users 表（与 3001 相同账号，报价小程序角色）。"""
    user, err = verify_quote_weapp_password(username, password)
    return user if not err else None
