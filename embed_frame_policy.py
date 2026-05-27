"""允许 3003 guanli 内嵌 iframe 加载 3001/3002 页面。"""
from __future__ import annotations

FRAME_ANCESTORS = (
    "frame-ancestors 'self' https://guanli.feijihe.top "
    "http://127.0.0.1:3003 http://localhost:3003"
)


def register_embed_parents(app) -> None:
    @app.after_request
    def _allow_guanli_embed(resp):
        existing = resp.headers.get("Content-Security-Policy") or ""
        if "frame-ancestors" not in existing:
            resp.headers["Content-Security-Policy"] = FRAME_ANCESTORS
        return resp
