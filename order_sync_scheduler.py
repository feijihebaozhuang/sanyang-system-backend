# -*- coding: utf-8 -*-
"""快麦/1688 订单后台同步调度：启动即全量、周期增量、失败自动重试。"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Callable

_started = False
_start_lock = threading.Lock()


def start_background_order_sync(
    cache_file: str | Path,
    *,
    memo_getter: Callable[[str], str] | None = None,
    include_1688_direct: bool = True,
    full_days_back: int = 30,
    incremental_days_back: int = 7,
    interval_sec: int = 180,
    on_after_sync: Callable[[dict[str, Any]], None] | None = None,
) -> None:
    """
    非阻塞启动后台同步线程。
    - 首次：全量（近 full_days_back 天）
    - 之后每 interval_sec 秒：增量（近 incremental_days_back 天，按 upd_time）
  - 失败指数退避重试，线程不退出
    """
    global _started
    with _start_lock:
        if _started:
            return
        _started = True

    cache_path = str(cache_file)

    def _loop() -> None:
        import order_sync as osync

        first = True
        fail_streak = 0
        while True:
            days = full_days_back if first else incremental_days_back
            label = "全量" if first else "增量"
            try:
                print(f"[订单同步] 开始{label}（近{days}天）…")
                report = osync.sync_orders_to_cache(
                    cache_path,
                    days_back=days,
                    memo_getter=memo_getter,
                    include_1688_direct=include_1688_direct,
                )
                fail_streak = 0
                if on_after_sync:
                    try:
                        on_after_sync(report)
                    except Exception as cb_ex:
                        print(f"[订单同步] 同步后回调异常: {cb_ex}")
            except Exception as ex:
                fail_streak += 1
                delay = min(300, 15 * (2 ** min(fail_streak - 1, 4)))
                print(
                    f"[订单同步] {label}失败(连续{fail_streak}次): {ex}，"
                    f"{delay}秒后重试"
                )
                time.sleep(delay)
                continue

            first = False
            time.sleep(max(60, int(interval_sec)))

    threading.Thread(
        target=_loop, daemon=True, name="order-sync-background"
    ).start()
    print(
        f"[订单同步] 后台已启动：启动全量{full_days_back}天，"
        f"每{interval_sec}秒增量{incremental_days_back}天"
    )
