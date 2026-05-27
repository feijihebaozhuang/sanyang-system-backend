# -*- coding: utf-8 -*-
"""feijihe.top(3002) → 3003 管理后台 API 反代，绕过 guanli 子域 Nginx IP 白名单。"""
from __future__ import annotations

import os
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

from flask import Response, request

if TYPE_CHECKING:
    from flask import Flask

CO_UPSTREAM = (os.getenv("CO_ADMIN_UPSTREAM") or "http://127.0.0.1:3003").rstrip("/")
CO_CORS_ORIGINS = {
    "https://guanli.feijihe.top",
    "http://guanli.feijihe.top",
    "https://www.guanli.feijihe.top",
    "http://www.guanli.feijihe.top",
    "https://feijihe.top",
    "http://feijihe.top",
    "https://www.feijihe.top",
    "http://www.feijihe.top",
}

_HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        "host",
        "content-length",
    }
)


def _cors_origin() -> str:
    origin = (request.headers.get("Origin") or "").strip()
    if origin in CO_CORS_ORIGINS:
        return origin
    if origin.endswith(".feijihe.top") or origin.endswith("feijihe.top"):
        return origin
    return "https://guanli.feijihe.top"


def _apply_cors(resp: Response) -> Response:
    resp.headers["Access-Control-Allow-Origin"] = _cors_origin()
    resp.headers["Access-Control-Allow-Credentials"] = "true"
    resp.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, X-Sanyang-User, X-Sanyang-Token, Authorization"
    )
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
    return resp


def _forward_to_3003(subpath: str) -> Response:
    qs = request.query_string.decode("utf-8", errors="ignore")
    url = f"{CO_UPSTREAM}/api/{subpath}"
    if qs:
        url = f"{url}?{qs}"
    headers = {}
    for k, v in request.headers:
        lk = k.lower()
        if lk in _HOP_BY_HOP:
            continue
        headers[k] = v
    body = request.get_data()
    req = urllib.request.Request(url, data=body or None, headers=headers, method=request.method)
    try:
        with urllib.request.urlopen(req, timeout=120) as upstream:
            data = upstream.read()
            status = upstream.status
            out_headers = []
            for k, v in upstream.headers.items():
                lk = k.lower()
                if lk in _HOP_BY_HOP or lk == "set-cookie":
                    if lk == "set-cookie":
                        out_headers.append((k, v))
                    continue
                out_headers.append((k, v))
    except urllib.error.HTTPError as e:
        data = e.read()
        status = e.code
        out_headers = list(e.headers.items()) if e.headers else []
    except Exception as e:
        return _apply_cors(
            Response(
                f'{{"success":false,"message":"3003 不可用: {e}"}}',
                status=502,
                mimetype="application/json",
            )
        )
    resp = Response(data, status=status)
    for k, v in out_headers:
        if k.lower() not in _HOP_BY_HOP:
            resp.headers[k] = v
    return _apply_cors(resp)


def register_co_admin_proxy(app: Flask, prefix: str = "/api/co") -> None:
    """注册 /api/co/* → 127.0.0.1:3003/api/*。"""

    @app.route(f"{prefix}/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
    def _co_admin_proxy(subpath: str):
        if request.method == "OPTIONS":
            return _apply_cors(Response("", status=204))
        return _forward_to_3003(subpath)
