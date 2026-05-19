# -*- coding: utf-8 -*-
"""访问即同步：读缓存秒回，后台增量拉单（防抖）。"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Any, Callable

_visit_lock = threading.Lock()
_state: dict[str, Any] = {
    "running": False,
    "last_started": 0.0,
    "last_finished": 0.0,
    "last_error": None,
    "last_report": None,
}

DEBOUNCE_SEC = int(os.getenv("VISIT_SYNC_DEBOUNCE_SEC", "45"))
INCREMENTAL_HOURS = int(os.getenv("VISIT_SYNC_HOURS", "6"))


def cache_updated_ago_sec() -> int | None:
    try:
        import order_cache_store as ocs

        meta = ocs.read_meta()
        ts = meta.get("updated_at")
        if not ts:
            return None
        return max(0, int(time.time() - float(ts)))
    except Exception:
        return None


def visit_sync_status() -> dict[str, Any]:
    with _visit_lock:
        ago = cache_updated_ago_sec()
        return {
            "running": bool(_state["running"]),
            "last_started": _state["last_started"],
            "last_finished": _state["last_finished"],
            "last_error": _state["last_error"],
            "updated_ago_sec": ago,
            "incremental_hours": INCREMENTAL_HOURS,
        }


def schedule_incremental_sync(
    cache_file: str | Path | None = None,
    *,
    memo_getter: Callable[[str], str] | None = None,
    include_1688_direct: bool = False,
    force: bool = False,
) -> bool:
    """若未在防抖窗口内，后台启动增量同步。返回是否已调度。"""
    now = time.time()
    with _visit_lock:
        if _state["running"]:
            return False
        if (
            not force
            and _state["last_started"]
            and now - _state["last_started"] < DEBOUNCE_SEC
        ):
            return False
        _state["running"] = True
        _state["last_started"] = now
        _state["last_error"] = None

    def _run():
        try:
            import order_sync as osync

            path = cache_file or osync.default_cache_path()
            rep = osync.sync_orders_incremental(
                path,
                hours_back=INCREMENTAL_HOURS,
                memo_getter=memo_getter,
                include_1688_direct=include_1688_direct,
            )
            with _visit_lock:
                _state["last_report"] = rep
        except Exception as ex:
            with _visit_lock:
                _state["last_error"] = str(ex)
            print(f"[访问即同步] 失败: {ex}")
        finally:
            with _visit_lock:
                _state["running"] = False
                _state["last_finished"] = time.time()

    threading.Thread(target=_run, daemon=True, name="visit-incremental-sync").start()
    return True
