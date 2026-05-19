# -*- coding: utf-8 -*-
"""订单缓存 MySQL 存储：同步写入、查询优先读库，JSON 文件作 fallback。"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Callable

import pymysql

_tables_ready = False
_tables_lock = threading.Lock()


def _db_config() -> dict:
    from settings import get_db_config

    return get_db_config()


def _connect():
    cfg = _db_config()
    return pymysql.connect(**cfg, cursorclass=pymysql.cursors.DictCursor)


def ensure_order_cache_tables() -> None:
    global _tables_ready
    if _tables_ready:
        return
    with _tables_lock:
        if _tables_ready:
            return
        db = _connect()
        cur = db.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS order_cache_meta (
                id TINYINT PRIMARY KEY DEFAULT 1,
                updated_at DOUBLE NOT NULL DEFAULT 0,
                source VARCHAR(64) DEFAULT '',
                shop_count INT DEFAULT 0,
                partial TINYINT(1) DEFAULT 0,
                report_json LONGTEXT,
                CONSTRAINT chk_single_meta CHECK (id = 1)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS order_cache_orders (
                so_id VARCHAR(64) PRIMARY KEY,
                tid VARCHAR(64) DEFAULT '',
                platform VARCHAR(32) DEFAULT '',
                order_status VARCHAR(64) DEFAULT '',
                status_label VARCHAR(64) DEFAULT '',
                shop_name VARCHAR(128) DEFAULT '',
                sync_source VARCHAR(32) DEFAULT '',
                created VARCHAR(32) DEFAULT '',
                pay_time VARCHAR(32) DEFAULT '',
                total_amount DECIMAL(14,2) DEFAULT 0,
                receiver_name VARCHAR(128) DEFAULT '',
                receiver_mobile VARCHAR(64) DEFAULT '',
                receiver_province VARCHAR(64) DEFAULT '',
                receiver_city VARCHAR(64) DEFAULT '',
                receiver_address VARCHAR(512) DEFAULT '',
                order_json LONGTEXT NOT NULL,
                updated_at DOUBLE NOT NULL DEFAULT 0,
                INDEX idx_platform (platform),
                INDEX idx_shop (shop_name),
                INDEX idx_created (created),
                INDEX idx_pay_time (pay_time)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS order_cache_items (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                so_id VARCHAR(64) NOT NULL,
                line_idx INT NOT NULL DEFAULT 0,
                sku VARCHAR(128) DEFAULT '',
                name VARCHAR(512) DEFAULT '',
                qty INT DEFAULT 0,
                price DECIMAL(14,2) DEFAULT 0,
                display VARCHAR(1024) DEFAULT '',
                spec VARCHAR(1024) DEFAULT '',
                item_json LONGTEXT,
                INDEX idx_so (so_id),
                CONSTRAINT fk_order_items_so
                    FOREIGN KEY (so_id) REFERENCES order_cache_orders(so_id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS stats_cache (
                cache_key VARCHAR(64) PRIMARY KEY,
                payload_json LONGTEXT NOT NULL,
                updated_at DOUBLE NOT NULL DEFAULT 0
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        db.commit()
        cur.close()
        db.close()
        _tables_ready = True


def mysql_cache_available() -> bool:
    try:
        ensure_order_cache_tables()
        db = _connect()
        cur = db.cursor()
        cur.execute("SELECT 1 FROM order_cache_meta WHERE id=1")
        cur.fetchone()
        cur.close()
        db.close()
        return True
    except Exception as e:
        print(f"[order_cache] MySQL 不可用: {e}")
        return False


def order_count_mysql() -> int:
    try:
        ensure_order_cache_tables()
        db = _connect()
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM order_cache_orders")
        row = cur.fetchone() or {}
        cur.close()
        db.close()
        return int(row.get("c") or 0)
    except Exception:
        return 0


def _order_row_from_dict(o: dict, updated_at: float) -> tuple:
    so_id = str(o.get("so_id") or "").strip()
    if not so_id:
        raise ValueError("missing so_id")
    return (
        so_id,
        str(o.get("tid") or o.get("platform_tid") or "")[:64],
        str(o.get("platform") or "")[:32],
        str(o.get("order_status") or "")[:64],
        str(o.get("status_label") or o.get("status") or "")[:64],
        str(o.get("shop_name") or "")[:128],
        str(o.get("sync_source") or "")[:32],
        str(o.get("created") or "")[:32],
        str(o.get("pay_time") or "")[:32],
        float(o.get("total_amount") or 0),
        str(o.get("receiver_name") or "")[:128],
        str(o.get("receiver_mobile") or "")[:64],
        str(o.get("receiver_province") or "")[:64],
        str(o.get("receiver_city") or "")[:64],
        str(o.get("receiver_address") or "")[:512],
        json.dumps(o, ensure_ascii=False, default=str),
        updated_at,
    )


def write_orders_snapshot(
    orders: list[dict],
    *,
    report: dict[str, Any] | None = None,
    shops_count: int = 0,
    source: str = "kuaimai+1688",
    partial: bool = False,
) -> int:
    """全量替换待发货订单缓存（与 JSON 快照语义一致）。"""
    ensure_order_cache_tables()
    updated_at = time.time()
    rep = dict(report or {})
    db = _connect()
    cur = db.cursor()
    try:
        cur.execute("DELETE FROM order_cache_items")
        cur.execute("DELETE FROM order_cache_orders")
        order_sql = """
            INSERT INTO order_cache_orders (
                so_id, tid, platform, order_status, status_label,
                shop_name, sync_source, created, pay_time, total_amount,
                receiver_name, receiver_mobile, receiver_province,
                receiver_city, receiver_address, order_json, updated_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        item_sql = """
            INSERT INTO order_cache_items (
                so_id, line_idx, sku, name, qty, price, display, spec, item_json
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        n = 0
        for o in orders:
            if not isinstance(o, dict):
                continue
            try:
                row = _order_row_from_dict(o, updated_at)
            except ValueError:
                continue
            cur.execute(order_sql, row)
            so_id = row[0]
            for idx, it in enumerate(o.get("items") or []):
                if not isinstance(it, dict):
                    continue
                cur.execute(
                    item_sql,
                    (
                        so_id,
                        idx,
                        str(it.get("sku") or "")[:128],
                        str(it.get("name") or "")[:512],
                        int(it.get("qty") or 0),
                        float(it.get("price") or 0),
                        str(it.get("display") or it.get("spec") or "")[:1024],
                        str(it.get("spec") or "")[:1024],
                        json.dumps(it, ensure_ascii=False, default=str),
                    ),
                )
            n += 1
        cur.execute(
            """
            INSERT INTO order_cache_meta (id, updated_at, source, shop_count, partial, report_json)
            VALUES (1, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                updated_at=VALUES(updated_at),
                source=VALUES(source),
                shop_count=VALUES(shop_count),
                partial=VALUES(partial),
                report_json=VALUES(report_json)
            """,
            (
                updated_at,
                source[:64],
                int(shops_count),
                1 if partial else 0,
                json.dumps(rep, ensure_ascii=False, default=str),
            ),
        )
        db.commit()
        return n
    except Exception:
        db.rollback()
        raise
    finally:
        cur.close()
        db.close()


def read_meta() -> dict[str, Any]:
    ensure_order_cache_tables()
    db = _connect()
    cur = db.cursor()
    cur.execute("SELECT * FROM order_cache_meta WHERE id=1")
    row = cur.fetchone()
    cur.close()
    db.close()
    if not row:
        return {}
    rep = {}
    try:
        rep = json.loads(row.get("report_json") or "{}")
    except json.JSONDecodeError:
        rep = {}
    return {
        "updated_at": row.get("updated_at"),
        "source": row.get("source"),
        "shop_count": row.get("shop_count"),
        "partial": bool(row.get("partial")),
        "report": rep,
    }


def read_orders_mysql(*, finalize: bool = True) -> list[dict]:
    ensure_order_cache_tables()
    db = _connect()
    cur = db.cursor()
    cur.execute(
        "SELECT order_json FROM order_cache_orders ORDER BY created DESC, so_id DESC"
    )
    rows = cur.fetchall()
    cur.close()
    db.close()
    orders: list[dict] = []
    for r in rows:
        try:
            o = json.loads(r["order_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(o, dict):
            orders.append(o)
    if finalize:
        try:
            import km_api as _km

            for o in orders:
                _km.finalize_cache_order(o)
        except ImportError:
            pass
    return orders


def find_order_mysql(query: str) -> dict | None:
    q = (query or "").strip()
    if not q:
        return None
    orders = read_orders_mysql(finalize=True)
    ql = q.lower()
    for o in orders:
        so_id = str(o.get("so_id") or "")
        tid = str(o.get("tid") or o.get("platform_tid") or "")
        if q == so_id or q == tid or ql in so_id.lower() or (tid and ql in tid.lower()):
            return o
    return None


def write_json_fallback(cache_path: Path, payload: dict[str, Any]) -> None:
    try:
        cache_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
    except OSError as e:
        print(f"[order_cache] JSON fallback 写入失败: {e}")


def read_json_fallback(cache_path: Path) -> dict[str, Any] | None:
    if not cache_path.is_file():
        return None
    try:
        with cache_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[order_cache] JSON fallback 读取失败: {e}")
        return None


def compute_dashboard_stats(
    orders: list[dict],
    store_workers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """与生产端 /api/dashboard summary 对齐的预计算。"""
    import production_helpers as ph

    store_workers = store_workers or {}
    all_orders: list[dict] = []
    for o in orders:
        items = o.get("items") or []
        product_parts = []
        total_qty = 0
        for item in items:
            spec = item.get("spec", "") or item.get("display", "") or ""
            qty = int(item.get("qty", 0) or 0)
            total_qty += qty
            if spec:
                product_parts.append(f"{spec}×{qty}")
        product_str = "; ".join(product_parts) if product_parts else "待确认"
        oid = ph.internal_order_id(o)
        shop_name = o.get("shop_name", "亚润")
        all_orders.append(
            {
                "id": oid,
                "store": shop_name,
                "worker": store_workers.get(shop_name, ""),
                "product": product_str,
                "qty": total_qty,
                "status": "待发货",
            }
        )
    total_all = len(all_orders)
    total_waiting = len([o for o in all_orders if o.get("status") == "待发货"])
    return {
        "summary": {
            "total_orders": total_all,
            "in_production": total_waiting,
            "waiting": total_waiting,
            "urgent_orders": 0,
            "completed": 0,
        },
        "order_count": total_all,
    }


def write_stats_cache(
    cache_key: str,
    payload: dict[str, Any],
) -> None:
    ensure_order_cache_tables()
    db = _connect()
    cur = db.cursor()
    cur.execute(
        """
        INSERT INTO stats_cache (cache_key, payload_json, updated_at)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE payload_json=VALUES(payload_json), updated_at=VALUES(updated_at)
        """,
        (cache_key, json.dumps(payload, ensure_ascii=False, default=str), time.time()),
    )
    db.commit()
    cur.close()
    db.close()


def read_stats_cache(cache_key: str) -> dict[str, Any] | None:
    try:
        ensure_order_cache_tables()
        db = _connect()
        cur = db.cursor()
        cur.execute(
            "SELECT payload_json, updated_at FROM stats_cache WHERE cache_key=%s",
            (cache_key,),
        )
        row = cur.fetchone()
        cur.close()
        db.close()
        if not row:
            return None
        data = json.loads(row["payload_json"] or "{}")
        data["_updated_at"] = row.get("updated_at")
        return data
    except Exception:
        return None


def import_json_file_to_mysql(
    cache_path: str | Path,
    *,
    store_workers: dict[str, str] | None = None,
) -> int:
    """一次性/冷启动：将 orders_cache.json 导入 MySQL。"""
    path = Path(cache_path)
    data = read_json_fallback(path)
    if not data:
        return 0
    orders = list(data.get("orders") or [])
    if not orders:
        return 0
    report = data.get("report") or {}
    n = write_orders_snapshot(
        orders,
        report=report,
        shops_count=int(data.get("shop_count") or 0),
        source=str(data.get("source") or "kuaimai+1688"),
        partial=bool(data.get("partial")),
    )
    stats = compute_dashboard_stats(orders, store_workers)
    write_stats_cache("dashboard_summary", stats)
    print(f"[order_cache] 已从 JSON 导入 {n} 条订单到 MySQL")
    return n


def auto_import_json_if_mysql_empty(cache_path: str | Path) -> int:
    if order_count_mysql() > 0:
        return 0
    path = Path(cache_path)
    if not path.is_file():
        return 0
    return import_json_file_to_mysql(path)


def load_orders_for_api(
    cache_path: str | Path,
    *,
    finalize: bool = True,
) -> tuple[list[dict], str, dict[str, Any]]:
    """
    查询优先 MySQL；空表且存在 JSON 则尝试导入；仍无数据则读 JSON fallback。
    返回 (orders, cache_status, meta)
    """
    path = Path(cache_path)
    meta: dict[str, Any] = {}

    if mysql_cache_available():
        auto_import_json_if_mysql_empty(path)
        n = order_count_mysql()
        if n > 0:
            meta = read_meta()
            return read_orders_mysql(finalize=finalize), "hit", meta
        if path.is_file():
            data = read_json_fallback(path)
            if data and data.get("orders"):
                orders = list(data.get("orders") or [])
                if finalize:
                    try:
                        import km_api as _km

                        for o in orders:
                            _km.finalize_cache_order(o)
                    except ImportError:
                        pass
                return orders, "json_fallback", {
                    "updated_at": data.get("updated_at"),
                    "report": data.get("report") or {},
                }
        return [], "waiting_sync", meta

    data = read_json_fallback(path)
    if not data:
        return [], "missing", meta
    orders = list(data.get("orders") or [])
    if finalize:
        try:
            import km_api as _km

            for o in orders:
                _km.finalize_cache_order(o)
        except ImportError:
            pass
    status = "hit" if orders else "empty"
    return orders, status, {
        "updated_at": data.get("updated_at"),
        "report": data.get("report") or {},
    }


def find_order(
    query: str,
    cache_path: str | Path,
) -> dict | None:
    if mysql_cache_available() and order_count_mysql() > 0:
        o = find_order_mysql(query)
        if o:
            return o
    path = Path(cache_path)
    data = read_json_fallback(path)
    if not data:
        return None
    q = (query or "").strip().lower()
    for o in data.get("orders") or []:
        so_id = str(o.get("so_id") or "")
        tid = str(o.get("tid") or o.get("platform_tid") or "")
        if query == so_id or query == tid or q in so_id.lower() or (tid and q in tid.lower()):
            return o
    return None
