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


def wx_code_to_session(code: str) -> dict[str, Any]:
    """wx.login code → openid/session_key；未配 AppSecret 时开发模式。"""
    code = (code or "").strip()
    if not code:
        raise ValueError("code 必填")
    appid = os.getenv("WX_MP_APPID", "").strip()
    secret = os.getenv("WX_MP_SECRET", "").strip()
    if not appid or not secret:
        oid = f"dev_{hashlib.sha256(code.encode()).hexdigest()[:20]}"
        return {"openid": oid, "session_key": "", "dev_mode": True}
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


def verify_cs_password(username: str, password: str) -> dict | None:
    """校验 users 表（与 3001 相同账号）。"""
    import hashlib as _hl

    import pymysql
    from settings import get_db_config

    username = (username or "").strip()
    if not username or not password:
        return None
    pwd_hash = _hl.sha256(password.encode()).hexdigest()
    cfg = dict(get_db_config())
    db = pymysql.connect(**cfg, cursorclass=pymysql.cursors.DictCursor)
    try:
        cur = db.cursor()
        cur.execute(
            "SELECT username, password, display_name, role, employee_name, enabled "
            "FROM users WHERE username=%s LIMIT 1",
            (username,),
        )
        row = cur.fetchone()
        cur.close()
    finally:
        db.close()
    if not row or not row.get("enabled", 1):
        return None
    if row.get("password") != pwd_hash:
        return None
    role = (row.get("role") or "").strip()
    if role not in ("客服", "管理", "超级管理员", "管理员", "主管"):
        return None
    return dict(row)
