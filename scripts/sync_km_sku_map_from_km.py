#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从快麦 item.list.query 全量同步 SKU → km_sku_map（20 万+）。

用法（87 stable 目录，需 km_token.json / .env）:
  python3 scripts/sync_km_sku_map_from_km.py
  python3 scripts/sync_km_sku_map_from_km.py --start-page 50 --resume
  python3 scripts/sync_km_sku_map_from_km.py --max-pages 5 --dry-run
  python3 scripts/sync_km_sku_map_from_km.py --enrich-order-cache

断点文件: data/km_sku_sync_checkpoint.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import km_api
import km_sku_map_store as kms
from settings import get_db_config

CHECKPOINT = ROOT / "data" / "km_sku_sync_checkpoint.json"


def _load_checkpoint() -> dict:
    if not CHECKPOINT.is_file():
        return {}
    try:
        return json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_checkpoint(state: dict) -> None:
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _enrich_from_order_cache(limit: int = 0) -> list[dict]:
    """从 order_cache_items 补 distinct sku（无尺寸时再调 single.sku.get）。"""
    import pymysql

    cfg = dict(get_db_config())
    cfg.pop("autocommit", None)
    db = pymysql.connect(**cfg, autocommit=True, cursorclass=pymysql.cursors.DictCursor)
    cur = db.cursor()
    sql = (
        "SELECT sku, MAX(spec) AS spec, MAX(name) AS name "
        "FROM order_cache_items WHERE sku IS NOT NULL AND sku != '' "
        "GROUP BY sku ORDER BY sku"
    )
    if limit > 0:
        sql += f" LIMIT {int(limit)}"
    cur.execute(sql)
    rows = cur.fetchall() or []
    cur.close()
    db.close()

    out: list[dict] = []
    existing = kms.load_all(force=True)
    for r in rows:
        sku = (r.get("sku") or "").strip()
        if not sku or sku in existing:
            continue
        rec = km_api.km_item_single_sku_get(sku_outer_id=sku)
        if rec:
            row = km_api.km_sku_record_to_map_row(rec)
            if row:
                out.append(row)
                continue
        spec = (r.get("spec") or r.get("name") or "").strip()
        pl, pw, ph, mat = kms.parse_spec_alias_dims(spec)
        out.append(
            {
                "outer_id": sku,
                "spec_alias": spec,
                "product_type": km_api.km_infer_product_type_from_title(spec, l=pl, w=pw),
                "length": pl,
                "width": pw,
                "height": ph,
                "dim_kind": kms.normalize_dim_kind(spec),
                "material": mat,
                "km_title": (r.get("name") or "").strip(),
            }
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="快麦商品库 → km_sku_map 全量同步")
    ap.add_argument("--page-size", type=int, default=200)
    ap.add_argument("--start-page", type=int, default=1)
    ap.add_argument("--max-pages", type=int, default=0, help="0=不限")
    ap.add_argument("--sleep", type=float, default=0.25, help="页间休眠秒")
    ap.add_argument("--batch", type=int, default=500, help="MySQL 批量写入大小")
    ap.add_argument("--resume", action="store_true", help="从 checkpoint 续跑")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--enrich-order-cache", action="store_true", help="同步后再从 order_cache_items 补 SKU")
    ap.add_argument("--active-status", type=int, default=1, help="1=启用 0=停用 -1=全部")
    args = ap.parse_args()

    if not km_api.km_configured():
        raise SystemExit("快麦未配置：请检查 km_token.json 或 KM_APP_KEY/SECRET/SESSION")

    start_page = max(1, args.start_page)
    ck = _load_checkpoint() if args.resume else {}
    if args.resume and ck.get("next_page"):
        start_page = int(ck["next_page"])
        print(f"续跑：从第 {start_page} 页开始（已写入 {ck.get('total_written', 0)} 行）")

    active = None if args.active_status < 0 else args.active_status
    max_pages = args.max_pages if args.max_pages > 0 else None
    buf: list[dict] = []
    total_written = int(ck.get("total_written") or 0) if args.resume else 0
    page = start_page
    pages_done = 0

    print(f"开始同步 item.list.query page_size={args.page_size} start={start_page}")

    while True:
        if max_pages is not None and pages_done >= max_pages:
            break
        res = km_api.km_item_list_query(
            page_no=page, page_size=args.page_size, active_status=active
        )
        items, total = km_api._km_item_list_payload(res)
        if not items:
            if page == start_page:
                msg = res.get("msg") or res.get("subMsg") or str(res)[:200]
                raise SystemExit(f"首屏无数据: {msg}")
            break

        page_rows: list[dict] = []
        for item in items:
            batch = km_api.km_catalog_rows_from_item(item)
            if not batch and int(item.get("isSkuItem") or 0) == 1:
                sid = item.get("sysItemId")
                if sid:
                    for sku in km_api.km_item_sku_list_get(sys_item_id=sid):
                        row = km_api.km_sku_record_to_map_row(
                            sku, item_title=item.get("title") or ""
                        )
                        if row:
                            batch.append(row)
                    if args.sleep:
                        time.sleep(args.sleep)
            page_rows.extend(batch)

        print(f"  页 {page}: items={len(items)} skus={len(page_rows)} total≈{total}")

        if args.dry_run:
            for r in page_rows[:3]:
                print("   ", r)
        else:
            buf.extend(page_rows)
            while len(buf) >= args.batch:
                chunk = buf[: args.batch]
                buf = buf[args.batch :]
                n = kms.upsert_rows(chunk)
                total_written += n

        if not args.dry_run:
            _save_checkpoint(
                {
                    "next_page": page + 1,
                    "total_written": total_written + len(buf),
                    "last_total": total,
                    "updated_at": time.time(),
                }
            )

        pages_done += 1
        if total and page * args.page_size >= total:
            break
        if len(items) < args.page_size:
            break
        page += 1
        if args.sleep:
            time.sleep(args.sleep)

    if buf and not args.dry_run:
        total_written += kms.upsert_rows(buf)
        buf.clear()

    if args.enrich_order_cache and not args.dry_run:
        print("补全 order_cache_items 中的 SKU …")
        extra = _enrich_from_order_cache()
        if extra:
            total_written += kms.upsert_rows(extra)
            print(f"  order_cache 补 {len(extra)} 行")

    final_count = kms.row_count()
    if not args.dry_run:
        _save_checkpoint(
            {
                "next_page": 1,
                "total_written": total_written,
                "completed_at": time.time(),
                "table_count": final_count,
            }
        )

    print(
        f"完成：本次写入约 {total_written} 行，km_sku_map 表现共 {final_count} 行"
        + (" (dry-run)" if args.dry_run else "")
    )


if __name__ == "__main__":
    main()
