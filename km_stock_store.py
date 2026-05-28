# -*- coding: utf-8 -*-
"""快麦可售库存只读镜像（km_stock_shadow）。"""
from __future__ import annotations

import threading
import time
from typing import Any

try:
    import pymysql
except ImportError:  # pragma: no cover
    pymysql = None  # type: ignore

_TABLE = "km_stock_shadow"

_CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS `{_TABLE}` (
  `outer_id` VARCHAR(128) NOT NULL COMMENT '商家编码',
  `warehouse_id` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '仓库ID',
  `warehouse_name` VARCHAR(128) NOT NULL DEFAULT '',
  `qty` DECIMAL(12,2) NOT NULL DEFAULT 0 COMMENT '库存数',
  `available_qty` DECIMAL(12,2) NOT NULL DEFAULT 0 COMMENT '可售',
  `lock_qty` DECIMAL(12,2) NOT NULL DEFAULT 0 COMMENT '锁定',
  `km_title` VARCHAR(256) NOT NULL DEFAULT '',
  `synced_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`outer_id`, `warehouse_id`),
  KEY `idx_wh` (`warehouse_id`),
  KEY `idx_synced` (`synced_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='快麦库存只读镜像';
"""

_cache_lock = threading.Lock()
_cache: dict[str, Any] = {"rows": [], "ts": 0.0}
_CACHE_TTL = float(__import__("os").getenv("KM_STOCK_CACHE_TTL_SEC", "120"))


def _get_db_config() -> dict:
    from settings import get_db_config

    return get_db_config()


def connect():
    if not pymysql:
        raise RuntimeError("缺少 pymysql")
    cfg = _get_db_config()
    cfg.pop("autocommit", None)
    return pymysql.connect(
        **cfg, autocommit=False, cursorclass=pymysql.cursors.DictCursor
    )


def mysql_available() -> bool:
    if not pymysql:
        return False
    try:
        db = connect()
        db.close()
        return True
    except Exception:
        return False


def ensure_schema(cur) -> None:
    cur.execute(_CREATE_SQL)


def invalidate_cache() -> None:
    with _cache_lock:
        _cache["ts"] = 0.0


def upsert_rows(rows: list[dict[str, Any]], *, batch_size: int = 500) -> int:
    if not rows:
        return 0
    db = connect()
    cur = db.cursor()
    ensure_schema(cur)
    sql = (
        f"INSERT INTO `{_TABLE}` "
        "(outer_id, warehouse_id, warehouse_name, qty, available_qty, lock_qty, km_title) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s) "
        "ON DUPLICATE KEY UPDATE "
        "warehouse_name=VALUES(warehouse_name), qty=VALUES(qty), "
        "available_qty=VALUES(available_qty), lock_qty=VALUES(lock_qty), "
        "km_title=VALUES(km_title), synced_at=CURRENT_TIMESTAMP"
    )
    buf: list[tuple] = []
    n = 0
    for r in rows:
        oid = (r.get("outer_id") or r.get("outerId") or "").strip()
        if not oid:
            continue
        wid = str(r.get("warehouse_id") or r.get("warehouseId") or "").strip()
        buf.append(
            (
                oid,
                wid,
                (r.get("warehouse_name") or r.get("warehouseName") or "").strip(),
                float(r.get("qty") or r.get("stock") or 0),
                float(r.get("available_qty") or r.get("availableStock") or r.get("available") or 0),
                float(r.get("lock_qty") or r.get("lockStock") or r.get("lock") or 0),
                (r.get("km_title") or r.get("title") or "").strip(),
            )
        )
        if len(buf) >= batch_size:
            cur.executemany(sql, buf)
            n += len(buf)
            buf.clear()
    if buf:
        cur.executemany(sql, buf)
        n += len(buf)
    db.commit()
    cur.close()
    db.close()
    invalidate_cache()
    return n


def row_count() -> int:
    try:
        db = connect()
        cur = db.cursor()
        ensure_schema(cur)
        cur.execute(f"SELECT COUNT(*) AS c FROM `{_TABLE}`")
        r = cur.fetchone()
        cur.close()
        db.close()
        return int((r or {}).get("c") or 0)
    except Exception:
        return 0


def lookup_outer_id(outer_id: str) -> list[dict[str, Any]]:
    code = (outer_id or "").strip()
    if not code:
        return []
    db = connect()
    try:
        cur = db.cursor()
        ensure_schema(cur)
        cur.execute(
            f"SELECT outer_id, warehouse_id, warehouse_name, qty, available_qty, lock_qty, "
            f"km_title, synced_at FROM `{_TABLE}` WHERE outer_id=%s",
            (code,),
        )
        return list(cur.fetchall() or [])
    finally:
        db.close()
