#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""独立快麦订单同步（供 systemd timer / cron 每分钟调用，不依赖有人打开页面）。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass


def main() -> int:
    ap = argparse.ArgumentParser(description="快麦待发货 → MySQL order_cache")
    ap.add_argument(
        "--mode",
        choices=("incremental", "full"),
        default="incremental",
        help="incremental=近 N 天待发货刷新；full=全量",
    )
    ap.add_argument("--days", type=int, default=0, help="覆盖天数（0=用环境变量）")
    args = ap.parse_args()

    import order_sync as osync

    days = args.days or int(__import__("os").getenv("ORDER_SYNC_INCREMENTAL_DAYS", "14"))
    if args.mode == "full":
        days = args.days or int(__import__("os").getenv("ORDER_SYNC_FULL_DAYS", "30"))
        report = osync.sync_orders_to_cache(days_back=days)
    else:
        report = osync.sync_orders_incremental(days_back=days)

    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    if report.get("skipped"):
        return 0
    if report.get("errors") and not report.get("pending_count"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
