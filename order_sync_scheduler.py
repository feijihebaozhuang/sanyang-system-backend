# -*- coding: utf-8 -*-
"""快麦 ERP 订单后台同步调度：启动即全量、周期刷新、MySQL 集群锁防多 worker 重复拉单。"""
from __future__ import annotations

import os
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
    include_1688_direct: bool = False,
    full_days_back: int = 30,
    incremental_days_back: int = 14,
    interval_sec: int = 45,
    on_after_sync: Callable[[dict[str, Any]], None] | None = None,
) -> None:
    """
    非阻塞启动后台同步线程（每个 Gunicorn worker 各启一线程，MySQL 锁保证同时只跑一个）。
    - 首次：全量近 full_days_back 天待发货
    - 之后每 interval_sec 秒：近 incremental_days_back 天待发货（快麦为准，剔除已发货）
    """
    global _started
    with _start_lock:
        if _started:
            return
        _started = True

    cache_path = str(cache_file)
    interval_sec = max(30, int(interval_sec))
    incremental_days_back = max(1, int(incremental_days_back))

    def _loop() -> None:
        import order_sync as osync

        first = True
        fail_streak = 0
        while True:
            days = full_days_back if first else incremental_days_back
            label = "全量" if first else "周期"
            try:
                print(f"[订单同步] 开始{label}（近{days}天待发货）…")
                if first:
                    report = osync.sync_orders_to_cache(
                        cache_path,
                        days_back=days,
                        memo_getter=memo_getter,
                        include_1688_direct=include_1688_direct,
                    )
                else:
                    report = osync.sync_orders_incremental(
                        cache_path,
                        days_back=days,
                        memo_getter=memo_getter,
                        include_1688_direct=include_1688_direct,
                    )
                if report.get("skipped"):
                    print(f"[订单同步] {label}跳过: {report.get('reason')}")
                else:
                    fail_streak = 0
                    if report.get("errors"):
                        print(
                            f"[订单同步] {label}完成但有 API 错误: "
                            f"{report.get('errors')[:2]}"
                        )
                    print(
                        f"[订单同步] {label}完成: 待发货 {report.get('pending_count', 0)} 条"
                    )
                if on_after_sync and not report.get("skipped"):
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
            time.sleep(interval_sec)

    threading.Thread(
        target=_loop, daemon=True, name="order-sync-background"
    ).start()
    print(
        f"[订单同步] 后台已启动：启动全量{full_days_back}天，"
        f"每{interval_sec}秒刷新近{incremental_days_back}天待发货"
    )
