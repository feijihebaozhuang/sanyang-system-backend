#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快麦订单独立同步脚本：不依赖 Flask/app 进程，可被 cron 独立调度。

每次运行：
  1. 读 MySQL 现有缓存订单 → map[so_id]
  2. 快麦拉取近 N 小时增量（按 upd_time）
  3. 合并 → 写回 MySQL
  4. 失败重试 10 次（30s 间隔）

用法：
  /www/feijihe/stable/venv/bin/python3 km_order_fetcher.py [--hours 2] [--full]
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# 确保在项目根目录下运行，能 import 同目录模块
_HERE = Path(__file__).resolve().parent
os.chdir(str(_HERE))
sys.path.insert(0, str(_HERE))

# 必须先加载 settings（触发 .env 加载），再 import 其他模块
import settings  # noqa: F401  triggers _ensure_dotenv()

import km_api
import order_cache_store as ocs


def _log(msg: str) -> None:
    print(f"[km_fetcher] {msg}", file=sys.stderr, flush=True)


def _check_db(retries: int = 10, delay: int = 30) -> bool:
    """检查 MySQL 是否可用，不可用则重试。"""
    for attempt in range(1, retries + 1):
        try:
            if ocs.mysql_cache_available():
                return True
            _log(f"MySQL 不可用，{delay}s 后重试 ({attempt}/{retries})")
        except Exception as e:
            _log(f"MySQL 检查异常: {e}，{delay}s 后重试 ({attempt}/{retries})")
        time.sleep(delay)
    return False


def main() -> int:
    # ---- 解析参数 ----
    hours_back = 2
    do_full = False
    for arg in sys.argv[1:]:
        if arg == "--full":
            do_full = True
        elif arg.startswith("--hours="):
            try:
                hours_back = max(1, int(arg.split("=", 1)[1]))
            except ValueError:
                pass
        elif arg.startswith("--"):
            _log(f"忽略未知参数: {arg}")

    start_ts = time.time()

    # ---- 检查 MySQL ----
    if not _check_db():
        _log("MySQL 无法连接，退出")
        return 1

    # ---- 检查快麦配置 ----
    if not km_api.km_configured():
        _log("快麦未配置（KM_APP_KEY 等环境变量），退出")
        return 1

    shops: dict[str, dict] = {}

    try:
        # ---- 读现有缓存 ----
        if do_full:
            _log("全量同步模式：将覆盖所有缓存")
            merged = {}
            shops = km_api.km_shop_lookup(refresh=True)
            _log(f"店铺数: {len(shops)}")
        else:
            merged = ocs.read_orders_as_map(finalize=False)
            _log(f"现有缓存: {len(merged)} 条")

        # ---- 快麦拉单 ----
        km_api.km_ensure_session()
        if not shops:
            shops = km_api.km_shop_lookup(refresh=do_full)

        if do_full:
            raw_out, err_out = km_api.km_fetch_trades_outstock(
                30,
                time_type="upd_time",
                status=km_api.KM_PENDING_STATUSES,
                source_filter=None,
            )
        else:
            raw_out, err_out = km_api.km_fetch_trades_outstock(
                1,
                hours_back=hours_back,
                time_type="upd_time",
                status=km_api.KM_PENDING_STATUSES,
                source_filter=None,
            )

        if err_out:
            for e in err_out[:3]:
                _log(f"快麦API错误: {e}")
        _log(f"快麦拉取: {len(raw_out)} 条")

        # ---- 合并 ----
        before = len(merged)
        for row in raw_out:
            if not isinstance(row, dict):
                continue
            o = km_api.km_trade_to_cache_order(row, shops)
            sid = str(o.get("so_id") or "").strip()
            if not sid:
                continue
            merged[sid] = o
        after = len(merged)
        new_count = after - before
        _log(f"合并完成: 新增 {new_count}，总计 {after}")

        # ---- 写入 MySQL ----
        pending_list = list(merged.values())

        report = {
            "km_outstock_count": len(raw_out),
            "pending_count": len(pending_list),
            "mode": "full" if do_full else "incremental",
            "hours_back": hours_back if not do_full else 0,
        }
        written = ocs.write_orders_snapshot(
            list(merged.values()),
            report=report,
            shops_count=len(shops),
            source="kuaimai_fetcher",
            partial=not do_full,
            allow_empty=do_full,
        )
        _log(f"写入 MySQL: {written} 条待发货")

        # ---- 刷新统计缓存 ----
        try:
            stats = ocs.compute_dashboard_stats(pending_list)
            ocs.write_stats_cache("dashboard_summary", stats)
        except Exception as e:
            _log(f"统计缓存更新失败 (非致命): {e}")

        elapsed = time.time() - start_ts
        _log(f"完成, 耗时 {elapsed:.1f}s")
        return 0

    except Exception as e:
        _log(f"同步异常: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
