# -*- coding: utf-8 -*-
"""三羊客户下单系统 — MySQL 存储层（5 表）。"""
from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime
from typing import Any

try:
    import pymysql
except ImportError:  # pragma: no cover
    pymysql = None  # type: ignore

_tables_ready = False
_tables_lock = threading.Lock()

_DEFAULT_CATEGORIES = [
    {
        "code": "zhengsquare",
        "name": "标准飞机盒",
        "sort_order": 10,
        "spec_fields": ["length", "width", "height", "material", "dim_kind"],
    },
    {
        "code": "daikou",
        "name": "带扣飞机盒",
        "sort_order": 20,
        "spec_fields": ["length", "width", "height", "material", "dim_kind"],
    },
    {
        "code": "koudi",
        "name": "扣底盒",
        "sort_order": 30,
        "spec_fields": ["length", "width", "height", "material", "dim_kind"],
    },
    {
        "code": "shuangcha",
        "name": "双插盒",
        "sort_order": 40,
        "spec_fields": ["length", "width", "height", "material", "dim_kind"],
    },
    {
        "code": "juxing",
        "name": "纸箱",
        "sort_order": 50,
        "spec_fields": ["length", "width", "height", "material", "dim_kind"],
    },
    {
        "code": "zhenzhenmian",
        "name": "珍珠棉",
        "sort_order": 60,
        "spec_fields": ["length", "width", "height", "material", "dim_kind"],
    },
]

_ORDER_STATUSES = (
    "draft",
    "pending_review",
    "approved",
    "rejected",
    "in_production",
    "completed",
    "cancelled",
)


def _db_config() -> dict:
    from settings import get_db_config

    return get_db_config()


def connect():
    if not pymysql:
        raise RuntimeError("缺少 pymysql")
    cfg = dict(_db_config())
    cfg.pop("autocommit", None)
    return pymysql.connect(**cfg, autocommit=False, cursorclass=pymysql.cursors.DictCursor)


def password_hash(plain: str) -> str:
    return hashlib.sha256(plain.encode()).hexdigest()


def ensure_schema(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS co_admin_user (
          id INT UNSIGNED NOT NULL AUTO_INCREMENT,
          username VARCHAR(64) NOT NULL,
          password_hash CHAR(64) NOT NULL,
          display_name VARCHAR(64) NOT NULL DEFAULT '',
          role VARCHAR(32) NOT NULL DEFAULT 'viewer',
          enabled TINYINT(1) NOT NULL DEFAULT 1,
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          UNIQUE KEY uk_username (username)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS co_product_category (
          id INT UNSIGNED NOT NULL AUTO_INCREMENT,
          code VARCHAR(64) NOT NULL,
          name VARCHAR(128) NOT NULL,
          sort_order INT NOT NULL DEFAULT 0,
          spec_fields_json JSON NULL,
          enabled TINYINT(1) NOT NULL DEFAULT 1,
          remark VARCHAR(512) NOT NULL DEFAULT '',
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          UNIQUE KEY uk_code (code),
          KEY idx_sort (sort_order)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS co_cs_staff (
          id INT UNSIGNED NOT NULL AUTO_INCREMENT,
          employee_name VARCHAR(64) NOT NULL,
          phone VARCHAR(32) NOT NULL DEFAULT '',
          enabled TINYINT(1) NOT NULL DEFAULT 1,
          remark VARCHAR(512) NOT NULL DEFAULT '',
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          UNIQUE KEY uk_employee_name (employee_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS co_customer (
          id INT UNSIGNED NOT NULL AUTO_INCREMENT,
          name VARCHAR(128) NOT NULL,
          contact_name VARCHAR(64) NOT NULL DEFAULT '',
          phone VARCHAR(32) NOT NULL DEFAULT '',
          company VARCHAR(256) NOT NULL DEFAULT '',
          assigned_cs_id INT UNSIGNED NULL,
          wx_openid VARCHAR(128) NOT NULL DEFAULT '',
          status VARCHAR(32) NOT NULL DEFAULT 'active',
          remark VARCHAR(512) NOT NULL DEFAULT '',
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          KEY idx_assigned_cs (assigned_cs_id),
          KEY idx_phone (phone),
          KEY idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS co_order (
          id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
          order_no VARCHAR(32) NOT NULL,
          customer_id INT UNSIGNED NOT NULL,
          cs_staff_id INT UNSIGNED NULL,
          product_category_code VARCHAR(64) NOT NULL DEFAULT '',
          length DECIMAL(10,2) NOT NULL DEFAULT 0,
          width DECIMAL(10,2) NOT NULL DEFAULT 0,
          height DECIMAL(10,2) NOT NULL DEFAULT 0,
          material VARCHAR(128) NOT NULL DEFAULT '',
          dim_kind VARCHAR(16) NOT NULL DEFAULT 'outer',
          outer_id VARCHAR(128) NOT NULL DEFAULT '',
          qty INT NOT NULL DEFAULT 0,
          unit_price DECIMAL(14,4) NOT NULL DEFAULT 0,
          total_price DECIMAL(14,2) NOT NULL DEFAULT 0,
          status VARCHAR(32) NOT NULL DEFAULT 'draft',
          remark VARCHAR(1024) NOT NULL DEFAULT '',
          created_by VARCHAR(64) NOT NULL DEFAULT '',
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          UNIQUE KEY uk_order_no (order_no),
          KEY idx_customer (customer_id),
          KEY idx_cs (cs_staff_id),
          KEY idx_status (status),
          KEY idx_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )


def ensure_tables() -> None:
    global _tables_ready
    if _tables_ready:
        return
    with _tables_lock:
        if _tables_ready:
            return
        db = connect()
        try:
            cur = db.cursor()
            ensure_schema(cur)
            _seed_defaults(cur)
            db.commit()
            _tables_ready = True
        finally:
            db.close()


def _seed_defaults(cur) -> None:
    cur.execute("SELECT COUNT(*) AS c FROM co_admin_user")
    if (cur.fetchone() or {}).get("c", 0) == 0:
        cur.execute(
            """
            INSERT INTO co_admin_user (username, password_hash, display_name, role, enabled)
            VALUES (%s, %s, %s, %s, 1)
            """,
            ("admin", password_hash("admin888"), "戴雅利", "admin"),
        )
    cur.execute("SELECT COUNT(*) AS c FROM co_product_category")
    if (cur.fetchone() or {}).get("c", 0) == 0:
        for cat in _DEFAULT_CATEGORIES:
            cur.execute(
                """
                INSERT INTO co_product_category (code, name, sort_order, spec_fields_json, enabled)
                VALUES (%s, %s, %s, %s, 1)
                """,
                (
                    cat["code"],
                    cat["name"],
                    cat["sort_order"],
                    json.dumps(cat["spec_fields"], ensure_ascii=False),
                ),
            )
    else:
        for cat in _DEFAULT_CATEGORIES:
            cur.execute("SELECT id FROM co_product_category WHERE code=%s LIMIT 1", (cat["code"],))
            if cur.fetchone():
                continue
            cur.execute(
                """
                INSERT INTO co_product_category (code, name, sort_order, spec_fields_json, enabled)
                VALUES (%s, %s, %s, %s, 1)
                """,
                (
                    cat["code"],
                    cat["name"],
                    cat["sort_order"],
                    json.dumps(cat["spec_fields"], ensure_ascii=False),
                ),
            )


def _json_load(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, (list, dict)):
        return val
    try:
        return json.loads(val)
    except (TypeError, json.JSONDecodeError):
        return val


def _row_category(row: dict | None) -> dict | None:
    if not row:
        return None
    out = dict(row)
    out["spec_fields"] = _json_load(out.pop("spec_fields_json", None)) or []
    return out


def get_admin_by_username(username: str) -> dict | None:
    ensure_tables()
    db = connect()
    try:
        cur = db.cursor()
        cur.execute(
            "SELECT id, username, password_hash, display_name, role, enabled FROM co_admin_user WHERE username=%s",
            (username,),
        )
        return cur.fetchone()
    finally:
        db.close()


def list_admin_users() -> list[dict]:
    ensure_tables()
    db = connect()
    try:
        cur = db.cursor()
        cur.execute(
            """
            SELECT id, username, display_name, role, enabled, created_at, updated_at
            FROM co_admin_user ORDER BY id ASC
            """
        )
        return list(cur.fetchall() or [])
    finally:
        db.close()


def upsert_admin_user(data: dict) -> dict:
    ensure_tables()
    username = (data.get("username") or "").strip()
    if not username:
        raise ValueError("username 必填")
    display_name = (data.get("display_name") or username).strip()
    role = (data.get("role") or "viewer").strip()
    if role not in ("admin", "viewer"):
        raise ValueError("role 只能是 admin 或 viewer")
    enabled = 1 if data.get("enabled", True) else 0
    uid = data.get("id")
    plain_pwd = (data.get("password") or "").strip()

    db = connect()
    try:
        cur = db.cursor()
        if uid:
            if plain_pwd:
                cur.execute(
                    """
                    UPDATE co_admin_user
                    SET username=%s, password_hash=%s, display_name=%s, role=%s, enabled=%s
                    WHERE id=%s
                    """,
                    (username, password_hash(plain_pwd), display_name, role, enabled, uid),
                )
            else:
                cur.execute(
                    """
                    UPDATE co_admin_user
                    SET username=%s, display_name=%s, role=%s, enabled=%s
                    WHERE id=%s
                    """,
                    (username, display_name, role, enabled, uid),
                )
        else:
            if not plain_pwd:
                raise ValueError("新建账号需填写 password")
            cur.execute(
                """
                INSERT INTO co_admin_user (username, password_hash, display_name, role, enabled)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (username, password_hash(plain_pwd), display_name, role, enabled),
            )
            uid = cur.lastrowid
        db.commit()
        cur.execute(
            "SELECT id, username, display_name, role, enabled, created_at, updated_at FROM co_admin_user WHERE id=%s",
            (uid,),
        )
        return cur.fetchone() or {}
    finally:
        db.close()


def list_categories(include_disabled: bool = False) -> list[dict]:
    ensure_tables()
    db = connect()
    try:
        cur = db.cursor()
        sql = "SELECT * FROM co_product_category"
        if not include_disabled:
            sql += " WHERE enabled=1"
        sql += " ORDER BY sort_order ASC, id ASC"
        cur.execute(sql)
        return [_row_category(r) for r in (cur.fetchall() or [])]
    finally:
        db.close()


def upsert_category(data: dict) -> dict:
    ensure_tables()
    code = (data.get("code") or "").strip()
    name = (data.get("name") or "").strip()
    if not code or not name:
        raise ValueError("code 和 name 必填")
    spec_fields = data.get("spec_fields") or ["length", "width", "height", "material", "dim_kind"]
    sort_order = int(data.get("sort_order") or 0)
    enabled = 1 if data.get("enabled", True) else 0
    remark = (data.get("remark") or "").strip()
    cid = data.get("id")

    db = connect()
    try:
        cur = db.cursor()
        if cid:
            cur.execute(
                """
                UPDATE co_product_category
                SET code=%s, name=%s, sort_order=%s, spec_fields_json=%s, enabled=%s, remark=%s
                WHERE id=%s
                """,
                (code, name, sort_order, json.dumps(spec_fields, ensure_ascii=False), enabled, remark, cid),
            )
        else:
            cur.execute(
                """
                INSERT INTO co_product_category (code, name, sort_order, spec_fields_json, enabled, remark)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (code, name, sort_order, json.dumps(spec_fields, ensure_ascii=False), enabled, remark),
            )
            cid = cur.lastrowid
        db.commit()
        cur.execute("SELECT * FROM co_product_category WHERE id=%s", (cid,))
        return _row_category(cur.fetchone()) or {}
    finally:
        db.close()


def list_cs_staff(include_disabled: bool = False) -> list[dict]:
    ensure_tables()
    db = connect()
    try:
        cur = db.cursor()
        sql = "SELECT * FROM co_cs_staff"
        if not include_disabled:
            sql += " WHERE enabled=1"
        sql += " ORDER BY employee_name ASC"
        cur.execute(sql)
        return list(cur.fetchall() or [])
    finally:
        db.close()


def upsert_cs_staff(data: dict) -> dict:
    ensure_tables()
    name = (data.get("employee_name") or "").strip()
    if not name:
        raise ValueError("employee_name 必填")
    phone = (data.get("phone") or "").strip()
    enabled = 1 if data.get("enabled", True) else 0
    remark = (data.get("remark") or "").strip()
    sid = data.get("id")

    db = connect()
    try:
        cur = db.cursor()
        if sid:
            cur.execute(
                """
                UPDATE co_cs_staff SET employee_name=%s, phone=%s, enabled=%s, remark=%s WHERE id=%s
                """,
                (name, phone, enabled, remark, sid),
            )
        else:
            cur.execute(
                """
                INSERT INTO co_cs_staff (employee_name, phone, enabled, remark)
                VALUES (%s, %s, %s, %s)
                """,
                (name, phone, enabled, remark),
            )
            sid = cur.lastrowid
        db.commit()
        cur.execute("SELECT * FROM co_cs_staff WHERE id=%s", (sid,))
        return cur.fetchone() or {}
    finally:
        db.close()


def list_customers(
    *,
    assigned_cs_id: int | None = None,
    keyword: str = "",
    status: str = "",
    limit: int = 200,
    offset: int = 0,
) -> tuple[list[dict], int]:
    ensure_tables()
    db = connect()
    try:
        cur = db.cursor()
        where = ["1=1"]
        params: list[Any] = []
        if assigned_cs_id:
            where.append("c.assigned_cs_id=%s")
            params.append(assigned_cs_id)
        if status:
            where.append("c.status=%s")
            params.append(status)
        if keyword:
            where.append("(c.name LIKE %s OR c.phone LIKE %s OR c.company LIKE %s)")
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw])
        wsql = " AND ".join(where)
        cur.execute(f"SELECT COUNT(*) AS c FROM co_customer c WHERE {wsql}", params)
        total = int((cur.fetchone() or {}).get("c") or 0)
        cur.execute(
            f"""
            SELECT c.*, s.employee_name AS assigned_cs_name
            FROM co_customer c
            LEFT JOIN co_cs_staff s ON s.id = c.assigned_cs_id
            WHERE {wsql}
            ORDER BY c.updated_at DESC, c.id DESC
            LIMIT %s OFFSET %s
            """,
            params + [limit, offset],
        )
        return list(cur.fetchall() or []), total
    finally:
        db.close()


def upsert_customer(data: dict) -> dict:
    ensure_tables()
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("name 必填")
    contact_name = (data.get("contact_name") or "").strip()
    phone = (data.get("phone") or "").strip()
    company = (data.get("company") or "").strip()
    assigned_cs_id = data.get("assigned_cs_id") or None
    if assigned_cs_id == "":
        assigned_cs_id = None
    status = (data.get("status") or "active").strip()
    remark = (data.get("remark") or "").strip()
    cid = data.get("id")

    db = connect()
    try:
        cur = db.cursor()
        if cid:
            cur.execute(
                """
                UPDATE co_customer
                SET name=%s, contact_name=%s, phone=%s, company=%s,
                    assigned_cs_id=%s, status=%s, remark=%s
                WHERE id=%s
                """,
                (name, contact_name, phone, company, assigned_cs_id, status, remark, cid),
            )
        else:
            cur.execute(
                """
                INSERT INTO co_customer
                (name, contact_name, phone, company, assigned_cs_id, status, remark)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (name, contact_name, phone, company, assigned_cs_id, status, remark),
            )
            cid = cur.lastrowid
        db.commit()
        cur.execute(
            """
            SELECT c.*, s.employee_name AS assigned_cs_name
            FROM co_customer c
            LEFT JOIN co_cs_staff s ON s.id = c.assigned_cs_id
            WHERE c.id=%s
            """,
            (cid,),
        )
        return cur.fetchone() or {}
    finally:
        db.close()


def _gen_order_no() -> str:
    return "CO" + datetime.now().strftime("%Y%m%d%H%M%S%f")[:18]


def list_orders(
    *,
    status: str = "",
    customer_id: int | None = None,
    cs_staff_id: int | None = None,
    keyword: str = "",
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict], int]:
    ensure_tables()
    db = connect()
    try:
        cur = db.cursor()
        where = ["1=1"]
        params: list[Any] = []
        if status:
            where.append("o.status=%s")
            params.append(status)
        if customer_id:
            where.append("o.customer_id=%s")
            params.append(customer_id)
        if cs_staff_id:
            where.append("o.cs_staff_id=%s")
            params.append(cs_staff_id)
        if keyword:
            where.append("(o.order_no LIKE %s OR c.name LIKE %s OR o.outer_id LIKE %s)")
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw])
        wsql = " AND ".join(where)
        cur.execute(
            f"""
            SELECT COUNT(*) AS c
            FROM co_order o
            LEFT JOIN co_customer c ON c.id = o.customer_id
            WHERE {wsql}
            """,
            params,
        )
        total = int((cur.fetchone() or {}).get("c") or 0)
        cur.execute(
            f"""
            SELECT o.*, c.name AS customer_name, c.phone AS customer_phone,
                   s.employee_name AS cs_name, pc.name AS category_name
            FROM co_order o
            LEFT JOIN co_customer c ON c.id = o.customer_id
            LEFT JOIN co_cs_staff s ON s.id = o.cs_staff_id
            LEFT JOIN co_product_category pc ON pc.code = o.product_category_code
            WHERE {wsql}
            ORDER BY o.created_at DESC, o.id DESC
            LIMIT %s OFFSET %s
            """,
            params + [limit, offset],
        )
        rows = list(cur.fetchall() or [])
        for r in rows:
            for k in ("length", "width", "height", "unit_price", "total_price"):
                if k in r and r[k] is not None:
                    r[k] = float(r[k])
        return rows, total
    finally:
        db.close()


def get_order(order_id: int) -> dict | None:
    ensure_tables()
    db = connect()
    try:
        cur = db.cursor()
        cur.execute(
            """
            SELECT o.*, c.name AS customer_name, c.phone AS customer_phone,
                   s.employee_name AS cs_name, pc.name AS category_name
            FROM co_order o
            LEFT JOIN co_customer c ON c.id = o.customer_id
            LEFT JOIN co_cs_staff s ON s.id = o.cs_staff_id
            LEFT JOIN co_product_category pc ON pc.code = o.product_category_code
            WHERE o.id=%s
            """,
            (order_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        for k in ("length", "width", "height", "unit_price", "total_price"):
            if k in row and row[k] is not None:
                row[k] = float(row[k])
        return row
    finally:
        db.close()


def upsert_order(data: dict, *, created_by: str = "admin") -> dict:
    ensure_tables()
    customer_id = int(data.get("customer_id") or 0)
    if not customer_id:
        raise ValueError("customer_id 必填")
    product_category_code = (data.get("product_category_code") or "").strip()
    length = float(data.get("length") or 0)
    width = float(data.get("width") or 0)
    height = float(data.get("height") or 0)
    material = (data.get("material") or "").strip()
    dim_kind = (data.get("dim_kind") or "outer").strip() or "outer"
    qty = int(data.get("qty") or 0)
    unit_price = float(data.get("unit_price") or 0)
    total_price = float(data.get("total_price") or 0)
    if not total_price and qty and unit_price:
        total_price = round(qty * unit_price, 2)
    status = (data.get("status") or "draft").strip()
    if status not in _ORDER_STATUSES:
        raise ValueError(f"无效 status: {status}")
    remark = (data.get("remark") or "").strip()
    cs_staff_id = data.get("cs_staff_id") or None
    if cs_staff_id == "":
        cs_staff_id = None
    outer_id = (data.get("outer_id") or "").strip()
    if not outer_id:
        match = lookup_sku_match(product_category_code, length, width, height, material, dim_kind)
        outer_id = (match or {}).get("outer_id") or ""

    oid = data.get("id")
    db = connect()
    try:
        cur = db.cursor()
        if oid:
            cur.execute(
                """
                UPDATE co_order SET
                  customer_id=%s, cs_staff_id=%s, product_category_code=%s,
                  length=%s, width=%s, height=%s, material=%s, dim_kind=%s,
                  outer_id=%s, qty=%s, unit_price=%s, total_price=%s,
                  status=%s, remark=%s
                WHERE id=%s
                """,
                (
                    customer_id, cs_staff_id, product_category_code,
                    length, width, height, material, dim_kind,
                    outer_id, qty, unit_price, total_price,
                    status, remark, oid,
                ),
            )
        else:
            order_no = _gen_order_no()
            cur.execute(
                """
                INSERT INTO co_order (
                  order_no, customer_id, cs_staff_id, product_category_code,
                  length, width, height, material, dim_kind, outer_id,
                  qty, unit_price, total_price, status, remark, created_by
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    order_no, customer_id, cs_staff_id, product_category_code,
                    length, width, height, material, dim_kind, outer_id,
                    qty, unit_price, total_price, status, remark, created_by,
                ),
            )
            oid = cur.lastrowid
        db.commit()
        return get_order(int(oid)) or {}
    finally:
        db.close()


def lookup_sku_match(
    product_type: str,
    length: float,
    width: float,
    height: float,
    material: str = "",
    dim_kind: str = "",
    *,
    tolerance: float = 0.01,
) -> dict | None:
    """在 km_sku_map 中按结构化规格查找匹配（只读）。"""
    ensure_tables()
    if not product_type or not length or not width or not height:
        return None
    db = connect()
    try:
        cur = db.cursor()
        params: list[Any] = [product_type, length, width, height]
        sql = """
            SELECT outer_id, spec_alias, product_type, length, width, height,
                   dim_kind, material, km_title
            FROM km_sku_map
            WHERE product_type=%s
              AND ABS(length - %s) < %s
              AND ABS(width - %s) < %s
              AND ABS(height - %s) < %s
        """
        params.extend([tolerance, tolerance, tolerance])
        if dim_kind:
            sql += " AND (dim_kind=%s OR dim_kind='')"
            params.append(dim_kind)
        if material:
            sql += " AND (material=%s OR material='')"
            params.append(material)
        sql += " ORDER BY updated_at DESC LIMIT 1"
        cur.execute(sql, params)
        row = cur.fetchone()
        if row:
            for k in ("length", "width", "height"):
                if row.get(k) is not None:
                    row[k] = float(row[k])
        return row
    except Exception:
        return None
    finally:
        db.close()


def dashboard_stats() -> dict:
    ensure_tables()
    db = connect()
    try:
        cur = db.cursor()
        stats: dict[str, int] = {}
        cur.execute("SELECT COUNT(*) AS c FROM co_customer WHERE status='active'")
        stats["customers_active"] = int((cur.fetchone() or {}).get("c") or 0)
        cur.execute("SELECT COUNT(*) AS c FROM co_product_category WHERE enabled=1")
        stats["categories_enabled"] = int((cur.fetchone() or {}).get("c") or 0)
        cur.execute("SELECT COUNT(*) AS c FROM co_cs_staff WHERE enabled=1")
        stats["cs_staff_enabled"] = int((cur.fetchone() or {}).get("c") or 0)
        cur.execute("SELECT COUNT(*) AS c FROM co_order")
        stats["orders_total"] = int((cur.fetchone() or {}).get("c") or 0)
        cur.execute("SELECT COUNT(*) AS c FROM co_order WHERE status='pending_review'")
        stats["orders_pending_review"] = int((cur.fetchone() or {}).get("c") or 0)
        return stats
    finally:
        db.close()
