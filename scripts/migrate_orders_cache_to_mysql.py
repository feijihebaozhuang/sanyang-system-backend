#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
订单缓存迁移：orders_cache.json 和/或旧 MySQL 表 orders_cache → order_cache_orders。

用法（项目根目录，已配置 .env 的 MYSQL_*）：
  python scripts/migrate_orders_cache_to_mysql.py
  python scripts/migrate_orders_cache_to_mysql.py --cache /path/to/orders_cache.json
  python scripts/migrate_orders_cache_to_mysql.py --from-table orders_cache
  python scripts/migrate_orders_cache_to_mysql.py --force   # 已有数据时先清空再导入

部署：deploy.sh / deploy-docker.sh 在表空时会自动执行（不 --force）。
应用启动：order_cache_store.bootstrap_order_cache_if_empty()（双容器用 GET_LOCK）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="orders_cache.json / 旧表 orders_cache → order_cache_orders"
    )
    parser.add_argument(
        "--cache",
        default="",
        help="orders_cache.json 路径（默认项目根 orders_cache.json）",
    )
    parser.add_argument(
        "--from-table",
        default="",
        help="旧 MySQL 表名，如 orders_cache（可与 --cache 同时尝试，JSON 优先）",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="MySQL 已有订单时先清空再导入",
    )
    args = parser.parse_args()

    import order_cache_store as ocs

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
        try:
            cur.execute("DELETE FROM order_cache_items")
            cur.execute("DELETE FROM order_cache_orders")
            cur.execute("DELETE FROM order_cache_meta WHERE id=1")
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            cur.close()
            db.close()
        print("[migrate] 已清空 MySQL 订单缓存表")

    cache_path = Path(args.cache) if args.cache else _ROOT / "orders_cache.json"
    if cache_path.is_file():
        n = ocs.import_json_file_to_mysql(cache_path)
        if n > 0:
            print(f"[migrate] JSON 完成，导入 {n} 条")
            return 0

    tables = [args.from_table] if args.from_table else ["orders_cache", "order_cache"]
    for table in tables:
        n = ocs.import_legacy_mysql_table(table)
        if n > 0:
            print(f"[migrate] 旧表 {table} 完成，导入 {n} 条")
            return 0

    if not cache_path.is_file() and not args.from_table:
        rep = ocs.bootstrap_order_cache_if_empty()
        if rep.get("status") == "ok":
            print(f"[migrate] 自动探测完成: {rep}")
            return 0
        print(f"[migrate] 未找到可导入数据源: {rep}")
        return 1

    print("[migrate] 未导入任何订单（检查 JSON 路径或 --from-table）")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
