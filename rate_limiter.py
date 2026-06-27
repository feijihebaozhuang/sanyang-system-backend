# -*- coding: utf-8 -*-
"""简易内存限速器：保护登录等敏感接口免受暴力破解。"""
from __future__ import annotations
import time
from functools import wraps
from typing import Callable, Any
_attempts: dict[str, list[float]] = {}
def rate_limit(limit: int = 5, window: int = 60) -> Callable:
    """限速装饰器：同一 IP 在 window 秒内最多发起 limit 次请求。超出时返回 429 JSON。"""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            from flask import jsonify, request
            ip = request.remote_addr or "unknown"
            key = f"{ip}:rate:{request.path}"
            now = time.time()
            history = _attempts.get(key, [])
            history = [t for t in history if now - t < window]
            if len(history) >= limit:
                return jsonify({"success": False, "message": "请求过于频繁，请稍后再试", "code": 429}), 429
            history.append(now)
            _attempts[key] = history
            return f(*args, **kwargs)
        return wrapper
    return decorator
def clear_rate_limit(ip: str | None = None) -> None:
    """清除指定 IP 的限速记录；ip=None 则清空全部。"""
    if ip:
        keys = [k for k in _attempts if ip in k]
        for k in keys:
            _attempts.pop(k, None)
    else:
        _attempts.clear()
