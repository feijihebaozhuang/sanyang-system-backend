# -*- coding: utf-8 -*-
"""订单缓存 MySQL 存储：同步写入、查询只读 MySQL。"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Callable

import pymysql

_tables_ready = False
_tables_lock = threading.Lock()
_startup_migrate_scheduled = False
_startup_migrate_lock = threading.Lock()
_MIGRATE_LOCK_NAME = "sanyang_order_cache_bootstrap"


def _db_config() -> dict:
    from settings import get_db_config

    return get_db_config()


def _connect():
    """订单缓存写操作必须显式 commit；禁用 settings 里的 autocommit=True。"""
    cfg = dict(_db_config())
    cfg.pop("autocommit", None)
    return pymysql.connect(**cfg, autocommit=False, cursorclass=pymysql.cursors.DictCursor)


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


def _hydrate_order_items(o: dict) -> None:
    """order_json 可能只有 items_json 字符串而无 items 数组（打单 full_items 依赖 items）。"""
    if not isinstance(o, dict):
        return
    existing = o.get("items")
    if isinstance(existing, list) and len(existing) > 0:
        return
    raw = o.get("items_json")
    if raw is None or raw == "":
        return
    if isinstance(raw, list):
        o["items"] = raw
        return
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return
        if isinstance(parsed, list):
            o["items"] = parsed
        elif isinstance(parsed, dict):
            o["items"] = [parsed]


def _order_row_from_dict(o: dict, updated_at: float) -> tuple:
    _hydrate_order_items(o)
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
    allow_empty: bool = False,
) -> int:
    """全量替换待发货订单缓存（与 JSON 快照语义一致）。"""
    ensure_order_cache_tables()
    existing = order_count_mysql()
    if not orders and existing > 0 and not allow_empty:
        print(
            f"[order_cache] 拒绝空快照覆盖已有 {existing} 条订单"
            "（同步失败或未拉单时请检查 KM/1688 配置）"
        )
        return existing
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
            _hydrate_order_items(o)
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
    ensure_order_cache_tables()
    db = _connect()
    cur = db.cursor()
    ql = q.lower()
    cur.execute(
        "SELECT order_json FROM order_cache_orders WHERE so_id=%s OR tid=%s LIMIT 1",
        (q, q),
    )
    row = cur.fetchone()
    if not row:
        cur.execute("SELECT order_json, so_id, tid FROM order_cache_orders")
        for r in cur.fetchall():
            try:
                o = json.loads(r["order_json"])
            except (TypeError, json.JSONDecodeError):
                continue
            _hydrate_order_items(o)
            so_id = str(o.get("so_id") or "")
            tid = str(o.get("tid") or o.get("platform_tid") or "")
            if q == so_id or q == tid or ql in so_id.lower() or (tid and ql in tid.lower()):
                row = r
                break
        else:
            row = None
    cur.close()
    db.close()
    if not row:
        return None
    try:
        o = json.loads(row["order_json"])
    except (TypeError, json.JSONDecodeError):
        return None
    _hydrate_order_items(o)
    try:
        import km_api as _km

        _km.finalize_cache_order(o)
    except ImportError:
        pass
    return o


def upsert_order(o: dict) -> None:
    """单条订单 upsert（Webhook / 增量补丁）。"""
    ensure_order_cache_tables()
    updated_at = time.time()
    row = _order_row_from_dict(o, updated_at)
    so_id = row[0]
    db = _connect()
    cur = db.cursor()
    try:
        cur.execute("DELETE FROM order_cache_items WHERE so_id=%s", (so_id,))
        cur.execute(
            """
            INSERT INTO order_cache_orders (
                so_id, tid, platform, order_status, status_label,
                shop_name, sync_source, created, pay_time, total_amount,
                receiver_name, receiver_mobile, receiver_province,
                receiver_city, receiver_address, order_json, updated_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
                tid=VALUES(tid), platform=VALUES(platform),
                order_status=VALUES(order_status), status_label=VALUES(status_label),
                shop_name=VALUES(shop_name), sync_source=VALUES(sync_source),
                created=VALUES(created), pay_time=VALUES(pay_time),
                total_amount=VALUES(total_amount),
                receiver_name=VALUES(receiver_name),
                receiver_mobile=VALUES(receiver_mobile),
                receiver_province=VALUES(receiver_province),
                receiver_city=VALUES(receiver_city),
                receiver_address=VALUES(receiver_address),
                order_json=VALUES(order_json), updated_at=VALUES(updated_at)
            """,
            row,
        )
        item_sql = """
            INSERT INTO order_cache_items (
                so_id, line_idx, sku, name, qty, price, display, spec, item_json
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
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
        cur.execute(
            """
            INSERT INTO order_cache_meta (id, updated_at, source, shop_count, partial, report_json)
            VALUES (1, %s, 'kuaimai+1688', 0, 0, '{}')
            ON DUPLICATE KEY UPDATE updated_at=VALUES(updated_at)
            """,
            (updated_at,),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        cur.close()
        db.close()


def delete_order(so_id: str) -> bool:
    sid = (so_id or "").strip()
    if not sid:
        return False
    ensure_order_cache_tables()
    db = _connect()
    cur = db.cursor()
    cur.execute("DELETE FROM order_cache_items WHERE so_id=%s", (sid,))
    cur.execute("DELETE FROM order_cache_orders WHERE so_id=%s", (sid,))
    n = cur.rowcount
    db.commit()
    cur.close()
    db.close()
    return n > 0


def read_orders_as_map(*, finalize: bool = False) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for o in read_orders_mysql(finalize=finalize):
        sid = str(o.get("so_id") or "").strip()
        if sid:
            out[sid] = o
    return out


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


def _default_json_cache_paths() -> list[Path]:
    import os

    root = Path(__file__).resolve().parent
    paths: list[Path] = []
    env_path = (os.getenv("ORDERS_CACHE_JSON") or "").strip()
    if env_path:
        paths.append(Path(env_path))
    paths.extend(
        [
            root / "orders_cache.json",
            Path("/app/orders_cache.json"),
        ]
    )
    seen: set[str] = set()
    out: list[Path] = []
    for p in paths:
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def _table_exists(cur, table: str) -> bool:
    cur.execute("SHOW TABLES LIKE %s", (table,))
    return bool(cur.fetchone())


def _column_names(cur, table: str) -> list[str]:
    cur.execute(f"SHOW COLUMNS FROM `{table}`")
    return [str(r.get("Field") or r[0]) for r in cur.fetchall()]


def _orders_from_json_blob(raw: Any) -> list[dict]:
    if isinstance(raw, dict):
        if isinstance(raw.get("orders"), list):
            out = [o for o in raw["orders"] if isinstance(o, dict)]
            for o in out:
                _hydrate_order_items(o)
            return out
        if raw.get("so_id"):
            _hydrate_order_items(raw)
            return [raw]
    if isinstance(raw, str) and raw.strip():
        try:
            return _orders_from_json_blob(json.loads(raw))
        except json.JSONDecodeError:
            return []
    return []


def import_legacy_mysql_table(table_name: str = "orders_cache") -> int:
    """从旧版 MySQL 表（如 orders_cache）导入；表不存在或无法解析时返回 0。"""
    ensure_order_cache_tables()
    db = _connect()
    cur = db.cursor()
    orders: list[dict] = []
    try:
        if not _table_exists(cur, table_name):
            return 0
        cols = _column_names(cur, table_name)
        lower = {c.lower(): c for c in cols}
        if "order_json" in lower:
            cur.execute(f"SELECT `{lower['order_json']}` FROM `{table_name}`")
            for row in cur.fetchall():
                orders.extend(_orders_from_json_blob(row.get(lower["order_json"])))
        elif "payload_json" in lower:
            cur.execute(f"SELECT `{lower['payload_json']}` FROM `{table_name}`")
            for row in cur.fetchall():
                orders.extend(_orders_from_json_blob(row.get(lower["payload_json"])))
        elif "payload" in lower:
            cur.execute(f"SELECT `{lower['payload']}` FROM `{table_name}`")
            for row in cur.fetchall():
                orders.extend(_orders_from_json_blob(row.get(lower["payload"])))
        elif "data" in lower:
            cur.execute(f"SELECT `{lower['data']}` FROM `{table_name}`")
            for row in cur.fetchall():
                orders.extend(_orders_from_json_blob(row.get(lower["data"])))
        else:
            cur.execute(f"SELECT * FROM `{table_name}` LIMIT 5000")
            for row in cur.fetchall():
                if isinstance(row, dict) and row.get("so_id"):
                    orders.append(row)
    except Exception as ex:
        try:
            db.rollback()
        except Exception:
            pass
        print(f"[order_cache] 读取旧表 {table_name} 失败: {ex}")
        return 0
    finally:
        cur.close()
        db.close()

    if not orders:
        return 0
    dedup: dict[str, dict] = {}
    for o in orders:
        sid = str(o.get("so_id") or "").strip()
        if sid:
            dedup[sid] = o
    orders = list(dedup.values())
    n = write_orders_snapshot(
        orders,
        report={"migrated_from": f"mysql:{table_name}"},
        source="legacy_mysql",
        allow_empty=True,
    )
    stats = compute_dashboard_stats(orders)
    write_stats_cache("dashboard_summary", stats)
    print(f"[order_cache] 已从 MySQL 表 {table_name} 导入 {n} 条订单")
    return n


def import_json_file_to_mysql(cache_path: str | Path) -> int:
    """从 orders_cache.json 导入 MySQL。"""
    path = Path(cache_path)
    if not path.is_file():
        return 0
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return 0
    orders = list(data.get("orders") or [])
    if not orders:
        return 0
    n = write_orders_snapshot(
        orders,
        report=data.get("report") or {},
        shops_count=int(data.get("shop_count") or 0),
        source=str(data.get("source") or "kuaimai+1688"),
        partial=bool(data.get("partial")),
        allow_empty=True,
    )
    stats = compute_dashboard_stats(orders)
    write_stats_cache("dashboard_summary", stats)
    print(f"[order_cache] 已从 JSON 导入 {n} 条订单到 MySQL")
    return n


def _acquire_bootstrap_lock(cur) -> bool:
    cur.execute("SELECT GET_LOCK(%s, 15)", (_MIGRATE_LOCK_NAME,))
    row = cur.fetchone()
    if isinstance(row, dict):
        return int(row.get(list(row.keys())[0]) or 0) == 1
    return int(row[0] if row else 0) == 1


def _release_bootstrap_lock(cur) -> None:
    try:
        cur.execute("SELECT RELEASE_LOCK(%s)", (_MIGRATE_LOCK_NAME,))
    except Exception:
        pass


def bootstrap_order_cache_if_empty(
    *,
    cache_json: str | Path | None = None,
    legacy_tables: tuple[str, ...] = ("orders_cache", "order_cache"),
) -> dict[str, Any]:
    """
    新表为空时：优先 JSON，再尝试旧 MySQL 表 orders_cache。
    多进程/双容器用 GET_LOCK 防重复导入。
    """
    ensure_order_cache_tables()
    existing = order_count_mysql()
    if existing > 0:
        return {"status": "skipped", "reason": "has_data", "count": existing}

    db = _connect()
    cur = db.cursor()
    if not _acquire_bootstrap_lock(cur):
        cur.close()
        db.close()
        return {"status": "skipped", "reason": "lock_busy"}
    try:
        if order_count_mysql() > 0:
            return {"status": "skipped", "reason": "has_data_race"}

        paths: list[Path] = []
        if cache_json:
            paths.append(Path(cache_json))
        paths.extend(_default_json_cache_paths())

        for path in paths:
            if path.is_file():
                n = import_json_file_to_mysql(path)
                if n > 0:
                    return {"status": "ok", "source": str(path), "count": n}

        for table in legacy_tables:
            n = import_legacy_mysql_table(table)
            if n > 0:
                return {"status": "ok", "source": f"mysql:{table}", "count": n}

        return {"status": "empty", "reason": "no_legacy_source"}
    finally:
        _release_bootstrap_lock(cur)
        cur.close()
        db.close()


def schedule_startup_migration() -> None:
    """应用启动时后台执行一次空表迁移（Docker/裸跑均适用）。"""
    global _startup_migrate_scheduled
    with _startup_migrate_lock:
        if _startup_migrate_scheduled:
            return
        _startup_migrate_scheduled = True

    def _run() -> None:
        try:
            rep = bootstrap_order_cache_if_empty()
            if rep.get("status") == "ok":
                print(f"[order_cache] 启动迁移完成: {rep}")
            elif rep.get("status") == "empty":
                print("[order_cache] 启动迁移：无 JSON/旧表数据源，等待同步线程填表")
        except Exception as ex:
            print(f"[order_cache] 启动迁移失败: {ex}")

    threading.Thread(
        target=_run, daemon=True, name="order-cache-bootstrap"
    ).start()


def load_orders_for_api(
    *,
    finalize: bool = True,
) -> tuple[list[dict], str, dict[str, Any]]:
    """只读 MySQL。空表返回 waiting_sync，由后台同步填充。"""
    meta: dict[str, Any] = {}
    if not mysql_cache_available():
        return [], "mysql_unavailable", meta
    n = order_count_mysql()
    if n > 0:
        meta = read_meta()
        return read_orders_mysql(finalize=finalize), "hit", meta
    return [], "waiting_sync", meta


def find_order(query: str) -> dict | None:
    if not mysql_cache_available():
        return None
    return find_order_mysql(query)
