# -*- coding: utf-8 -*-
"""3002 上 /guanli/login/submit：服务端表单登录 3003，写 Cookie 后跳转（不依赖浏览器 fetch）。"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from flask import redirect, request

CO_UPSTREAM = (os.getenv("CO_ADMIN_UPSTREAM") or "http://127.0.0.1:3003").rstrip("/")
AUTH_COOKIE_USER = "sanyang_auth_user"
AUTH_COOKIE_TOKEN = "sanyang_auth_token"
COOKIE_MAX_AGE = 86400 * 31


def verify_co_token(username: str, token: str) -> bool:
    return fetch_co_user(username, token) is not None


def fetch_co_user(username: str, token: str) -> dict | None:
    username = (username or "").strip()
    token = (token or "").strip()
    if not username or not token:
        return None
    url = f"{CO_UPSTREAM}/api/me"
    req = urllib.request.Request(
        url,
        headers={"X-Sanyang-User": username, "X-Sanyang-Token": token},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("success") and data.get("user"):
                return data["user"]
    except Exception:
        pass
    return None


def read_guanli_auth_from_request() -> tuple[str, str] | tuple[None, None]:
    user = (request.cookies.get(AUTH_COOKIE_USER) or "").strip()
    token = (request.cookies.get(AUTH_COOKIE_TOKEN) or "").strip()
    if user and token and verify_co_token(user, token):
        return user, token
    return None, None


def inject_preauth_html(html: str, user: dict) -> str:
    payload = json.dumps(user, ensure_ascii=False)
    snippet = f"<script>window.__SY_PREAUTH={payload};</script>"
    if "<head>" in html:
        return html.replace("<head>", "<head>" + snippet, 1)
    return snippet + html


def _login_3003(username: str, password: str) -> dict:
    url = f"{CO_UPSTREAM}/api/login"
    body = json.dumps({"username": username, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _redirect_login(error: str = "") -> redirect:
    qs = f"?error={error}" if error else ""
    return redirect(f"/guanli/login{qs}")


def handle_guanli_form_login():
    """POST /guanli/login/submit — 传统表单，手机/任意浏览器均可用。"""
    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()
    if not username or not password:
        return _redirect_login("empty")

    try:
        data = _login_3003(username, password)
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read().decode("utf-8", errors="ignore") or "{}")
        except Exception:
            data = {}
        msg = (data.get("message") or data.get("error") or "").strip()
        if "密码" in msg or "账号" in msg:
            return _redirect_login("auth")
        return _redirect_login("server")
    except Exception:
        return _redirect_login("server")

    if not data.get("success") or not data.get("user"):
        return _redirect_login("auth")

    user = data["user"]
    token = (user.get("auth_token") or "").strip()
    uname = (user.get("username") or username).strip()
    if not token:
        return _redirect_login("server")

    resp = redirect("/guanli/")
    secure = (request.headers.get("X-Forwarded-Proto") or request.scheme or "").lower() == "https"
    for key, val in (
        (AUTH_COOKIE_USER, uname),
        (AUTH_COOKIE_TOKEN, token),
    ):
        resp.set_cookie(
            key,
            val,
            max_age=COOKIE_MAX_AGE,
            path="/",
            samesite="Lax",
            secure=secure,
            httponly=False,
        )
    return resp
