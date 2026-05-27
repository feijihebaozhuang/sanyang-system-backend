# -*- coding: utf-8 -*-
"""feijihe.top/guanli/ 内嵌 iframe：同源反代 3001/3002，绕过 zean CSP frame-ancestors 限制。"""
from __future__ import annotations

import os
import re
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

from flask import Response, request

if TYPE_CHECKING:
    from flask import Flask

CS_UPSTREAM = (os.getenv("CS_EMBED_UPSTREAM") or "http://127.0.0.1:3001").rstrip("/")
PROD_UPSTREAM = (os.getenv("PROD_EMBED_UPSTREAM") or "http://127.0.0.1:3002").rstrip("/")

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
        "content-encoding",
    }
)

_STRIP_RESP = frozenset({"x-frame-options", "content-security-policy"})


def _inject_base_html(body: bytes, base_href: str) -> bytes:
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return body
    if "<html" not in text.lower():
        return body
    base_tag = f'<base href="{base_href}">'
    if re.search(r"<base\s", text, re.I):
        text = re.sub(r"<base\s[^>]*>", base_tag, text, count=1, flags=re.I)
    else:
        text = re.sub(r"(<head[^>]*>)", r"\1\n    " + base_tag, text, count=1, flags=re.I)
    return text.encode("utf-8")


def _rewrite_location(loc: str, embed_prefix: str, upstream: str) -> str:
    loc = (loc or "").strip()
    if not loc:
        return loc
    for prefix in (upstream, upstream.replace("127.0.0.1", "localhost")):
        if loc.startswith(prefix + "/"):
            loc = loc[len(prefix) :]
            break
        if loc == prefix:
            loc = "/"
            break
    if loc.startswith("/"):
        return embed_prefix.rstrip("/") + loc
    return loc


def _forward_embed(upstream: str, embed_prefix: str, subpath: str) -> Response:
    path = (subpath or "").lstrip("/")
    url = f"{upstream}/{path}" if path else f"{upstream}/"
    qs = request.query_string.decode("utf-8", errors="ignore")
    if qs:
        url = f"{url}?{qs}"

    headers = {}
    for k, v in request.headers:
        lk = k.lower()
        if lk in _HOP_BY_HOP:
            continue
        headers[k] = v
    headers["Host"] = request.host
    headers["X-Forwarded-For"] = request.headers.get("X-Forwarded-For") or request.remote_addr or ""
    headers["X-Forwarded-Proto"] = request.scheme

    body = request.get_data()
    req = urllib.request.Request(url, data=body or None, headers=headers, method=request.method)
    try:
        with urllib.request.urlopen(req, timeout=120) as up:
            data = up.read()
            status = up.status
            out_headers = list(up.headers.items())
    except urllib.error.HTTPError as e:
        data = e.read()
        status = e.code
        out_headers = list(e.headers.items()) if e.headers else []
    except Exception as e:
        return Response(
            f"内嵌页上游不可用: {e}",
            status=502,
            mimetype="text/plain; charset=utf-8",
        )

    ctype = ""
    for k, v in out_headers:
        if k.lower() == "content-type":
            ctype = v.lower()
            break
    if "text/html" in ctype:
        base_href = embed_prefix if embed_prefix.endswith("/") else embed_prefix + "/"
        data = _inject_base_html(data, base_href)

    resp = Response(data, status=status)
    for k, v in out_headers:
        lk = k.lower()
        if lk in _HOP_BY_HOP or lk in _STRIP_RESP:
            continue
        if lk == "location":
            v = _rewrite_location(v, embed_prefix, upstream)
        resp.headers[k] = v
    resp.headers.pop("X-Frame-Options", None)
    resp.headers.pop("Content-Security-Policy", None)
    return resp


def register_guanli_embed_proxy(app: Flask) -> None:
    """注册 /guanli/embed/cs/* → 3001、/guanli/embed/prod/* → 3002。"""

    @app.route("/guanli/embed/cs/", defaults={"subpath": ""}, methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    @app.route("/guanli/embed/cs/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    def _embed_cs(subpath: str):
        return _forward_embed(CS_UPSTREAM, "/guanli/embed/cs/", subpath)

    @app.route("/guanli/embed/prod/", defaults={"subpath": ""}, methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    @app.route("/guanli/embed/prod/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    def _embed_prod(subpath: str):
        return _forward_embed(PROD_UPSTREAM, "/guanli/embed/prod/", subpath)
