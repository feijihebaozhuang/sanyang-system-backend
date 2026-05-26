# -*- coding: utf-8 -*-
"""客户下单小程序 — access_token、客服消息下发。"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

_token_lock = threading.Lock()
_token_cache: dict[str, Any] = {"token": "", "expires_at": 0.0}


def _customer_appid() -> str:
    return (os.getenv("WX_MP_APPID") or "").strip()


def _customer_secret() -> str:
    return (os.getenv("WX_MP_SECRET") or "").strip()


def customer_mp_configured() -> bool:
    return bool(_customer_appid() and _customer_secret())


def get_customer_access_token(*, force: bool = False) -> str:
    if not customer_mp_configured():
        raise RuntimeError("未配置客户小程序 WX_MP_APPID / WX_MP_SECRET")
    now = time.time()
    with _token_lock:
        if not force and _token_cache.get("token") and float(_token_cache.get("expires_at") or 0) > now + 60:
            return str(_token_cache["token"])
        url = (
            "https://api.weixin.qq.com/cgi-bin/token"
            f"?grant_type=client_credential"
            f"&appid={urllib.parse.quote(_customer_appid())}"
            f"&secret={urllib.parse.quote(_customer_secret())}"
        )
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise RuntimeError(f"获取 access_token 失败: {e}") from e
        if data.get("errcode"):
            raise RuntimeError(data.get("errmsg") or f"微信 errcode {data.get('errcode')}")
        token = (data.get("access_token") or "").strip()
        if not token:
            raise RuntimeError("微信未返回 access_token")
        ttl = int(data.get("expires_in") or 7200)
        _token_cache["token"] = token
        _token_cache["expires_at"] = now + max(300, ttl - 120)
        return token


def send_customer_service_text(openid: str, content: str) -> dict[str, Any]:
    """向客户下单小程序用户下发客服文本消息（客户可在微信里直接回复）。"""
    openid = (openid or "").strip()
    content = (content or "").strip()
    if not openid:
        return {"success": False, "error": "客户 openid 为空"}
    if not content:
        return {"success": False, "error": "消息内容为空"}
    if openid.startswith("dev_"):
        return {
            "success": True,
            "dev_mode": True,
            "msg": "开发模式 openid，未真实发送",
        }
    if not customer_mp_configured():
        return {"success": False, "error": "未配置客户小程序 AppSecret"}

    token = get_customer_access_token()
    payload = {
        "touser": openid,
        "msgtype": "text",
        "text": {"content": content[:2048]},
    }
    url = (
        "https://api.weixin.qq.com/cgi-bin/message/custom/send"
        f"?access_token={urllib.parse.quote(token)}"
    )
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return {"success": False, "error": f"发送失败: {e}"}

    err = int(data.get("errcode") or 0)
    if err == 0:
        return {"success": True, "wechat": data}

    errmsg = (data.get("errmsg") or "").strip()
    hint = _cs_send_error_hint(err, errmsg)
    return {
        "success": False,
        "error": hint,
        "errcode": err,
        "wechat": data,
    }


def _cs_send_error_hint(errcode: int, errmsg: str) -> str:
    if errcode in (45015, 45047, 48001):
        return (
            "暂时无法主动发起对话：客户需先在「客户下单小程序」点过一次「联系客服」，"
            "或 48 小时内与客服有过消息。可先拨打电话，或复制手机号添加微信。"
        )
    if errcode == 40001:
        return "微信 access_token 失效，请稍后重试"
    if errcode == 45002:
        return "消息内容过长"
    return errmsg or f"微信发送失败 errcode={errcode}"
