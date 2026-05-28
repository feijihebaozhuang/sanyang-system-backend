# -*- coding: utf-8 -*-
"""快麦商品编码 → km_sku_map 同步（增量/全量 + 订单未知编码回填）。"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import km_api
import km_sku_map_store as kms

_ROOT = Path(__file__).resolve().parent
CHECKPOINT = _ROOT / "data" / "km_sku_sync_checkpoint.json"


def _load_checkpoint() -> dict[str, Any]:
    if not CHECKPOINT.is_file():
        return {}
    try:
        return json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_checkpoint(state: dict[str, Any]) -> None:
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _fmt_km_time(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _process_item_page(
    items: list[dict],
    *,
    sleep: float,
) -> list[dict]:
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
                if sleep:
                    time.sleep(sleep)
        page_rows.extend(batch)
    return page_rows


def sync_catalog_pages(
    *,
    start_page: int = 1,
    max_pages: int | None = None,
    page_size: int = 200,
    active_status: int | None = 1,
    start_modified: str = "",
    end_modified: str = "",
    sleep: float = 0.25,
    batch: int = 500,
    dry_run: bool = False,
    resume: bool = False,
) -> dict[str, Any]:
    """分页拉 item.list.query 写入 km_sku_map。"""
    if not km_api.km_configured():
        return {"ok": False, "error": "快麦未配置"}

    ck = _load_checkpoint() if resume else {}
    page = max(1, start_page)
    if resume and ck.get("next_page"):
        page = int(ck["next_page"])

    buf: list[dict] = []
    total_written = int(ck.get("total_written") or 0) if resume else 0
    pages_done = 0
    last_total = 0

    while True:
        if max_pages is not None and pages_done >= max_pages:
            break
        res = km_api.km_item_list_query(
            page_no=page,
            page_size=page_size,
            active_status=active_status,
            start_modified=start_modified,
            end_modified=end_modified,
        )
        items, total = km_api._km_item_list_payload(res)
        last_total = total
        if not items:
            if page == start_page and not start_modified:
                msg = res.get("msg") or res.get("subMsg") or str(res)[:200]
                return {"ok": False, "error": f"首屏无数据: {msg}"}
            break

        page_rows = _process_item_page(items, sleep=sleep)
        if dry_run:
            pass
        else:
            buf.extend(page_rows)
            while len(buf) >= batch:
                chunk = buf[:batch]
                buf = buf[batch:]
                total_written += kms.upsert_rows(chunk)

        if not dry_run:
            _save_checkpoint(
                {
                    "mode": "pages",
                    "next_page": page + 1,
                    "total_written": total_written + len(buf),
                    "last_total": total,
                    "start_modified": start_modified,
                    "end_modified": end_modified,
                    "updated_at": time.time(),
                }
            )

        pages_done += 1
        if total and page * page_size >= total:
            break
        if len(items) < page_size:
            break
        page += 1
        if sleep:
            time.sleep(sleep)

    if buf and not dry_run:
        total_written += kms.upsert_rows(buf)

    return {
        "ok": True,
        "written": total_written,
        "pages": pages_done,
        "approx_total": last_total,
        "dry_run": dry_run,
    }


def sync_incremental(
    *,
    hours_back: int | None = None,
    overlap_hours: int | None = None,
    page_size: int = 200,
    sleep: float = 0.25,
    batch: int = 500,
) -> dict[str, Any]:
    """按修改时间增量同步快麦商品 → km_sku_map。"""
    if hours_back is None:
        hours_back = int(os.getenv("KM_SKU_SYNC_HOURS", "8"))
    if overlap_hours is None:
        overlap_hours = int(os.getenv("KM_SKU_SYNC_OVERLAP_HOURS", "1"))

    ck = _load_checkpoint()
    now = datetime.now()
    end_dt = now
    start_dt = end_dt - timedelta(hours=max(1, hours_back))

    if ck.get("last_modified_end"):
        try:
            prev_end = datetime.strptime(str(ck["last_modified_end"]), "%Y-%m-%d %H:%M:%S")
            start_dt = prev_end - timedelta(hours=max(0, overlap_hours))
        except ValueError:
            pass

    start_modified = _fmt_km_time(start_dt)
    end_modified = _fmt_km_time(end_dt)

    rep = sync_catalog_pages(
        start_page=1,
        max_pages=None,
        page_size=page_size,
        active_status=1,
        start_modified=start_modified,
        end_modified=end_modified,
        sleep=sleep,
        batch=batch,
        dry_run=False,
        resume=False,
    )
    if rep.get("ok"):
        _save_checkpoint(
            {
                "mode": "incremental",
                "last_modified_end": end_modified,
                "last_modified_start": start_modified,
                "written": rep.get("written", 0),
                "completed_at": time.time(),
                "table_count": kms.row_count(),
            }
        )
        rep["start_modified"] = start_modified
        rep["end_modified"] = end_modified
        rep["table_count"] = kms.row_count()
    return rep


def sync_full(
    *,
    page_size: int = 200,
    sleep: float = 0.25,
    batch: int = 500,
    resume: bool = False,
    max_pages: int | None = None,
) -> dict[str, Any]:
    """全量分页同步（首次或每周维护）。"""
    rep = sync_catalog_pages(
        start_page=1,
        max_pages=max_pages,
        page_size=page_size,
        active_status=1,
        sleep=sleep,
        batch=batch,
        dry_run=False,
        resume=resume,
    )
    if rep.get("ok"):
        _save_checkpoint(
            {
                "mode": "full",
                "next_page": 1,
                "written": rep.get("written", 0),
                "completed_at": time.time(),
                "table_count": kms.row_count(),
            }
        )
        rep["table_count"] = kms.row_count()
    return rep


def enrich_unknown_skus_from_orders(*, limit: int | None = None) -> dict[str, Any]:
    """从 order_cache_items 补 km_sku_map 中缺失的商家编码。"""
    if limit is None:
        limit = int(os.getenv("KM_SKU_ENRICH_PER_SYNC", "30"))
    limit = max(0, int(limit))
    if limit <= 0:
        return {"ok": True, "enriched": 0, "skipped": True}

    try:
        import pymysql
        from settings import get_db_config
    except ImportError as e:
        return {"ok": False, "error": str(e)}

    if not km_api.km_configured():
        return {"ok": False, "error": "快麦未配置"}

    cfg = dict(get_db_config())
    cfg.pop("autocommit", None)
    db = pymysql.connect(**cfg, autocommit=True, cursorclass=pymysql.cursors.DictCursor)
    cur = db.cursor()
    cur.execute(
        "SELECT sku, MAX(spec) AS spec, MAX(name) AS name "
        "FROM order_cache_items WHERE sku IS NOT NULL AND sku != '' "
        "GROUP BY sku ORDER BY sku DESC"
    )
    rows = cur.fetchall() or []
    cur.close()
    db.close()

    existing = kms.load_all(force=True)
    missing = [r for r in rows if (r.get("sku") or "").strip() not in existing]
    if not missing:
        return {"ok": True, "enriched": 0, "candidates": 0}

    to_fetch = missing[:limit]
    out: list[dict] = []
    for r in to_fetch:
        sku = (r.get("sku") or "").strip()
        if not sku:
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

    n = kms.upsert_rows(out) if out else 0
    return {
        "ok": True,
        "enriched": n,
        "candidates": len(missing),
        "fetched": len(to_fetch),
    }
