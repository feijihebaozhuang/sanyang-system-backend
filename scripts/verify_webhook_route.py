#!/usr/bin/env python3
"""部署探活：确认 Flask url_map 含 /api/webhook/kuaimai。"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

os.environ.setdefault("MYSQL_PASSWORD", "probe")
os.environ.setdefault("FLASK_SECRET_KEY", "probe-secret")


def _check(module_name: str) -> None:
    mod = __import__(module_name)
    app = mod.app
    rules = {r.rule for r in app.url_map.iter_rules()}
    for path in ("/api/webhook/kuaimai", "/api/webhook/feishu"):
        if path not in rules:
            raise SystemExit(f"{module_name}: missing {path} in url_map")
    print(f"OK {module_name} webhooks registered")


def main() -> int:
    _check("app_cs")
    _check("app_production")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
