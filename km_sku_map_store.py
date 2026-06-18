# -*- coding: utf-8 -*-
"""快麦商家编码 → 生产规格映射（轻量层，不镜像全量商品档案）。"""
from __future__ import annotations

import re
import threading
import time
from typing import Any

try:
    import pymysql
except ImportError:  # pragma: no cover
    pymysql = None  # type: ignore

_TABLE = "km_sku_map"

_CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS `{_TABLE}` (
  `outer_id` VARCHAR(128) NOT NULL COMMENT '商家编码/outerId',
  `spec_alias` VARCHAR(512) NOT NULL DEFAULT '' COMMENT '规格别名（生产解析用）',
  `product_type` VARCHAR(64) NOT NULL DEFAULT '' COMMENT 'zhengsquare/juxing/...',
  `length` DECIMAL(10,2) NOT NULL DEFAULT 0,
  `width` DECIMAL(10,2) NOT NULL DEFAULT 0,
  `height` DECIMAL(10,2) NOT NULL DEFAULT 0,
  `dim_kind` VARCHAR(16) NOT NULL DEFAULT '' COMMENT 'inner/outer/空',
  `material` VARCHAR(128) NOT NULL DEFAULT '',
  `km_title` VARCHAR(256) NOT NULL DEFAULT '' COMMENT '快麦简称，仅展示',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`outer_id`),
  KEY `idx_spec_alias` (`spec_alias`(191)),
  KEY `idx_dims` (`product_type`, `length`, `width`, `height`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='快麦商家编码生产映射';
"""

_SELECT_COLS = (
    "outer_id",
    "spec_alias",
    "product_type",
    "length",
    "width",
    "height",
    "dim_kind",
    "material",
    "km_title",
    "km_short_name",
    "exec_standard",
    "remark",
    "category",
    "updated_at",
)

_cache_lock = threading.Lock()
_cache: dict[str, Any] = {"by_outer": {}, "ts": 0.0}
_CACHE_TTL = float(__import__("os").getenv("KM_SKU_MAP_CACHE_TTL_SEC", "300"))


def _get_db_config() -> dict:
    from settings import get_db_config

    return get_db_config()


def connect():
    if not pymysql:
        raise RuntimeError("缺少 pymysql")
    cfg = _get_db_config()
    # settings 已经包含 autocommit，移除避免重复
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


def _row_to_dict(r: dict) -> dict[str, Any]:
    return {
        "outer_id": (r.get("outer_id") or "").strip(),
        "spec_alias": (r.get("spec_alias") or "").strip(),
        "product_type": (r.get("product_type") or "").strip(),
        "length": float(r.get("length") or 0),
        "width": float(r.get("width") or 0),
        "height": float(r.get("height") or 0),
        "dim_kind": (r.get("dim_kind") or "").strip().lower(),
        "material": (r.get("material") or "").strip(),
        "km_title": (r.get("km_title") or "").strip(),
        "km_short_name": (r.get("km_short_name") or "").strip(),
        "exec_standard": (r.get("exec_standard") or "").strip(),
        "remark": (r.get("remark") or "").strip(),
        "category": (r.get("category") or "").strip(),
        "updated_at": r.get("updated_at"),
    }


def invalidate_cache() -> None:
    with _cache_lock:
        _cache["ts"] = 0.0


def load_all(*, force: bool = False) -> dict[str, dict[str, Any]]:
    """outer_id → row"""
    now = time.time()
    with _cache_lock:
        if (
            not force
            and _cache["by_outer"]
            and now - float(_cache["ts"] or 0) < _CACHE_TTL
        ):
            return dict(_cache["by_outer"])
    try:
        db = connect()
        cur = db.cursor()
        ensure_schema(cur)
        cols = ", ".join(_SELECT_COLS)
        cur.execute(f"SELECT {cols} FROM `{_TABLE}`")
        rows = [_row_to_dict(r) for r in cur.fetchall()]
        cur.close()
        db.commit()
        db.close()
        by_outer = {r["outer_id"]: r for r in rows if r.get("outer_id")}
        with _cache_lock:
            _cache["by_outer"] = by_outer
            _cache["ts"] = now
        return dict(by_outer)
    except Exception as e:
        print(f"[km_sku_map] 加载失败: {e}")
        return {}


def lookup_outer_id(outer_id: str, index: dict[str, dict] | None = None) -> dict[str, Any] | None:
    code = (outer_id or "").strip()
    if not code:
        return None
    idx = index if index is not None else load_all()
    row = idx.get(code)
    if row:
        return row
    # 大小写不敏感兜底
    for k, v in idx.items():
        if k.lower() == code.lower():
            return v
    return None


def production_dims_from_map(row: dict[str, Any]) -> tuple[float, float, float]:
    """内径映射转外径生产尺寸（与报价规则一致）。"""
    l = float(row.get("length") or 0)
    w = float(row.get("width") or 0)
    h = float(row.get("height") or 0)
    kind = (row.get("dim_kind") or "").lower()
    if kind == "inner" and l and w:
        return l + 1.5, w + 0.5, (h + 0.5) if h else h
    return l, w, h


def map_has_production_dims(row: dict[str, Any] | None) -> bool:
    """映射表是否含可用于覆盖订单解析的长宽（已按 dim_kind 转外径）。"""
    if not row:
        return False
    l, w, _h = production_dims_from_map(row)
    return bool(l and w)


def upsert_rows(rows: list[dict[str, Any]], *, batch_size: int = 500) -> int:
    if not rows:
        return 0
    db = connect()
    cur = db.cursor()
    ensure_schema(cur)
    n = 0
    sql = (
        f"INSERT INTO `{_TABLE}` "
        "(outer_id, spec_alias, product_type, length, width, height, dim_kind, material, km_title, km_short_name, exec_standard, remark, category) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
        "ON DUPLICATE KEY UPDATE "
        "spec_alias=VALUES(spec_alias), product_type=VALUES(product_type), "
        "length=VALUES(length), width=VALUES(width), height=VALUES(height), "
        "dim_kind=VALUES(dim_kind), material=VALUES(material), km_title=VALUES(km_title), "
        "km_short_name=VALUES(km_short_name), exec_standard=VALUES(exec_standard), remark=VALUES(remark), category=VALUES(category)"
    )
    buf: list[tuple] = []
    for r in rows:
        oid = (r.get("outer_id") or "").strip()
        if not oid:
            continue
        buf.append(
            (
                oid,
                (r.get("spec_alias") or "").strip(),
                (r.get("product_type") or "").strip(),
                float(r.get("length") or 0),
                float(r.get("width") or 0),
                float(r.get("height") or 0),
                (r.get("dim_kind") or "").strip().lower(),
                (r.get("material") or "").strip(),
                (r.get("km_title") or "").strip(),
                (r.get("km_short_name") or "").strip(),
                (r.get("exec_standard") or "").strip(),
                (r.get("remark") or "").strip(),
                (r.get("category") or "").strip(),
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


def parse_spec_alias_dims(text: str) -> tuple[float, float, float, str]:
    """从「5x5x2国产纸」类字符串解析尺寸与材料。"""
    s = (text or "").strip()
    if not s:
        return 0.0, 0.0, 0.0, ""
    m = re.match(
        r"^(\d+(?:\.\d+)?)\s*[x×*]\s*(\d+(?:\.\d+)?)\s*[x×*]\s*(\d+(?:\.\d+)?)\s*(.*)$",
        s,
        re.I,
    )
    if not m:
        return 0.0, 0.0, 0.0, s
    try:
        return float(m.group(1)), float(m.group(2)), float(m.group(3)), (m.group(4) or "").strip()
    except ValueError:
        return 0.0, 0.0, 0.0, s


def normalize_product_type(raw: str, *, l: float = 0, w: float = 0) -> str:
    t = (raw or "").strip().lower()
    if t in ("zhengsquare", "正方形", "正方"):
        return "zhengsquare"
    if t in ("juxing", "changfang", "长方形", "长方"):
        return "juxing"
    if t in ("daikou", "带扣"):
        return "daikou"
    if l and w and abs(l - w) < 0.01:
        return "zhengsquare"
    if l and w:
        return "juxing"
    return t or "juxing"


def normalize_dim_kind(raw: str) -> str:
    s = (raw or "").strip().lower()
    if s in ("inner", "内", "内径", "nei"):
        return "inner"
    if s in ("outer", "外", "外径", "wai"):
        return "outer"
    return ""


def search_rows(
    *,
    keyword: str = "",
    outer_id: str = "",
    product_type: str = "",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """分页搜索 km_sku_map（不加载全表）。"""
    limit = max(1, min(int(limit or 50), 200))
    offset = max(0, int(offset or 0))
    where = ["1=1"]
    params: list[Any] = []
    oid = (outer_id or "").strip()
    if oid:
        where.append("outer_id LIKE %s")
        params.append(f"%{oid}%")
    pt = (product_type or "").strip()
    if pt:
        where.append("product_type=%s")
        params.append(pt)
    kw = (keyword or "").strip()
    if kw:
        where.append(
            "(outer_id LIKE %s OR spec_alias LIKE %s OR km_title LIKE %s OR material LIKE %s)"
        )
        like = f"%{kw}%"
        params.extend([like, like, like, like])
    wsql = " AND ".join(where)
    db = connect()
    try:
        cur = db.cursor()
        ensure_schema(cur)
        cur.execute(f"SELECT COUNT(*) AS c FROM `{_TABLE}` WHERE {wsql}", params)
        total = int((cur.fetchone() or {}).get("c") or 0)
        cols = ", ".join(_SELECT_COLS)
        cur.execute(
            f"SELECT {cols} FROM `{_TABLE}` WHERE {wsql} ORDER BY updated_at DESC LIMIT %s OFFSET %s",
            params + [limit, offset],
        )
        rows = [_row_to_dict(r) for r in cur.fetchall() or []]
        return rows, total
    finally:
        db.close()


def upsert_one(row: dict[str, Any]) -> dict[str, Any]:
    """单条写入/修正 SKU 映射（手工维护用）。"""
    oid = (row.get("outer_id") or "").strip()
    if not oid:
        raise ValueError("outer_id 必填")
    upsert_rows([row], batch_size=1)
    db = connect()
    try:
        cur = db.cursor()
        cols = ", ".join(_SELECT_COLS)
        cur.execute(f"SELECT {cols} FROM `{_TABLE}` WHERE outer_id=%s LIMIT 1", (oid,))
        r = cur.fetchone()
        return _row_to_dict(r) if r else _row_to_dict(row)
    finally:
        db.close()


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
