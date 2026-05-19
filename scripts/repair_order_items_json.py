#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 MySQL order_json：items_json → items，并合并 order_cache_items 子单表。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="修复订单缓存 items 字段")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="最多修复条数，0 表示全部",
    )
    args = parser.parse_args()

    import order_cache_store as ocs

    if not ocs.mysql_cache_available():
        print("[repair] MySQL 不可用")
        return 1
    n = ocs.repair_orders_items_in_mysql(limit=args.limit or 0)
    ocs._invalidate_production_dashboard_cache()
    print(f"[repair] 完成，修复 {n} 条；请刷新打单页（或 ?refresh=1）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
