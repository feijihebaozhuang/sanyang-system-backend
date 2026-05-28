#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快麦仓库库存 → km_stock_shadow 只读镜像（systemd / cron）。"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
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
    ap = argparse.ArgumentParser(description="快麦库存只读镜像")
    ap.add_argument("--page-size", type=int, default=200)
    ap.add_argument("--max-pages", type=int, default=0, help="0=不限")
    ap.add_argument("--sleep", type=float, default=0.3)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    import km_api
    import km_stock_store as kss

    if not km_api.km_configured():
        print(json.dumps({"ok": False, "error": "快麦未配置"}, ensure_ascii=False))
        return 1
    if not kss.mysql_available():
        print(json.dumps({"ok": False, "error": "MySQL 不可用"}, ensure_ascii=False))
        return 1

    km_api.km_ensure_session()
    page = 1
    pages = 0
    written = 0
    max_pages = args.max_pages if args.max_pages > 0 else None
    last_total = 0
    api_ok = False

    while True:
        if max_pages is not None and pages >= max_pages:
            break
        res = km_api.km_item_warehouse_list_get(
            page_no=page, page_size=args.page_size
        )
        rows, total = km_api._km_stock_list_payload(res)
        if rows:
            api_ok = True
        elif page == 1 and not km_api._km_stock_list_ok(res):
            msg = res.get("msg") or res.get("subMsg") or str(res)[:300]
            print(
                json.dumps(
                    {"ok": False, "error": msg, "raw_keys": list(res.keys())[:20]},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 1
        if not rows:
            break

        last_total = total
        shadow = []
        for r in rows:
            s = km_api.km_stock_row_to_shadow(r)
            if s:
                shadow.append(s)

        if not args.dry_run and shadow:
            written += kss.upsert_rows(shadow)

        pages += 1
        if total and page * args.page_size >= total:
            break
        if len(rows) < args.page_size:
            break
        page += 1
        if args.sleep:
            time.sleep(args.sleep)

    rep = {
        "ok": api_ok or pages > 0,
        "written": written,
        "pages": pages,
        "approx_total": last_total,
        "table_count": kss.row_count() if not args.dry_run else 0,
        "dry_run": args.dry_run,
    }
    print(json.dumps(rep, ensure_ascii=False, indent=2, default=str))
    return 0 if rep.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
