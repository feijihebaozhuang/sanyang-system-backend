#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一次性迁移：将 orders_cache.json 导入 MySQL（order_cache_orders / order_cache_items）。

用法（在项目根目录，已配置 .env 的 MYSQL_*）：
  python scripts/migrate_orders_cache_to_mysql.py
  python scripts/migrate_orders_cache_to_mysql.py --cache /path/to/orders_cache.json
  python scripts/migrate_orders_cache_to_mysql.py --force   # MySQL 已有数据时仍覆盖

部署后首次上线建议在 stable 目录执行本脚本，再重启 3001/3002。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="orders_cache.json → MySQL")
    parser.add_argument(
        "--cache",
        default=str(_ROOT / "orders_cache.json"),
        help="orders_cache.json 路径",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="MySQL 已有订单时先清空再导入",
    )
    args = parser.parse_args()
    cache_path = Path(args.cache)

    import order_cache_store as ocs

    if not cache_path.is_file():
        print(f"[migrate] 未找到缓存文件: {cache_path}")
        return 1

    ocs.ensure_order_cache_tables()
    existing = ocs.order_count_mysql()
    if existing > 0 and not args.force:
        print(
            f"[migrate] MySQL 已有 {existing} 条订单，跳过。"
            " 使用 --force 覆盖导入。"
        )
        return 0

    if existing > 0 and args.force:
        db = ocs._connect()
        cur = db.cursor()
        cur.execute("DELETE FROM order_cache_items")
        cur.execute("DELETE FROM order_cache_orders")
        cur.execute("DELETE FROM order_cache_meta WHERE id=1")
        db.commit()
        cur.close()
        db.close()
        print("[migrate] 已清空 MySQL 订单缓存表")

    n = ocs.import_json_file_to_mysql(cache_path)
    print(f"[migrate] 完成，导入 {n} 条待发货订单")
    return 0 if n >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
