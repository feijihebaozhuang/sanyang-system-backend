"""允许 3003 管理后台（feijihe.top/guanli/）内嵌 iframe 加载 3001/3002 页面。"""
from __future__ import annotations

# 父页面可能是 feijihe.top/guanli/ 或 guanli 子域，须全部放行
FRAME_ANCESTORS = (
    "frame-ancestors 'self' "
    "https://feijihe.top http://feijihe.top "
    "https://www.feijihe.top http://www.feijihe.top "
    "https://guanli.feijihe.top http://guanli.feijihe.top "
    "https://*.feijihe.top "
    "http://127.0.0.1:3003 http://localhost:3003 "
    "http://127.0.0.1:3002 http://localhost:3002"
)


def register_embed_parents(app) -> None:
    @app.after_request
    def _allow_guanli_embed(resp):
        resp.headers.pop("X-Frame-Options", None)
        existing = resp.headers.get("Content-Security-Policy") or ""
        if "frame-ancestors" not in existing:
            resp.headers["Content-Security-Policy"] = FRAME_ANCESTORS
        return resp
