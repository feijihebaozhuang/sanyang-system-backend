# -*- coding: utf-8 -*-
"""刀模库 MySQL 读写（客服端 / 生产端共用）。"""
from __future__ import annotations

from typing import Any, Callable

_EXTRA_COLUMNS: tuple[tuple[str, str], ...] = (
    ("code", "VARCHAR(64) NOT NULL DEFAULT ''"),
    ("production_spec", "VARCHAR(512) NOT NULL DEFAULT ''"),
    ("km_mapping_code", "VARCHAR(128) NOT NULL DEFAULT ''"),
)

_SELECT_COLS = (
    "id",
    "product_type",
    "name",
    "code",
    "production_spec",
    "km_mapping_code",
    "length",
    "width",
    "height",
    "remark",
    "stock",
    "created_at",
)


def ensure_dimoldb_schema(cur) -> None:
    for col, spec in _EXTRA_COLUMNS:
        cur.execute("SHOW COLUMNS FROM dimoldb LIKE %s", (col,))
        if not cur.fetchone():
            cur.execute(f"ALTER TABLE dimoldb ADD COLUMN `{col}` {spec}")


def _row_to_dict(r: dict) -> dict[str, Any]:
    return {
        "id": r["id"],
        "product_type": r["product_type"] or "",
        "name": r["name"] or "",
        "code": (r.get("code") or "") if isinstance(r, dict) else "",
        "production_spec": (r.get("production_spec") or "") if isinstance(r, dict) else "",
        "km_mapping_code": (r.get("km_mapping_code") or "") if isinstance(r, dict) else "",
        "length": float(r["length"]) if r["length"] else 0,
        "width": float(r["width"]) if r["width"] else 0,
        "height": float(r["height"]) if r["height"] else 0,
        "remark": r["remark"] or "",
        "stock": r["stock"] or 0,
        "created_at": r["created_at"] or "",
    }


def load_dimoldb(get_db: Callable) -> list[dict[str, Any]]:
    try:
        db = get_db()
        cur = db.cursor()
        ensure_dimoldb_schema(cur)
        cols = ", ".join(_SELECT_COLS)
        cur.execute(f"SELECT {cols} FROM dimoldb ORDER BY created_at DESC")
        rows = cur.fetchall()
        result = [_row_to_dict(r) for r in rows]
        cur.close()
        db.close()
        return result
    except Exception as e:
        print(f"[MySQL load_dimoldb] 错误: {e}")
        return []


def save_dimoldb(get_db: Callable, data: list[dict]) -> bool:
    try:
        db = get_db()
        cur = db.cursor()
        ensure_dimoldb_schema(cur)
        cur.execute("TRUNCATE TABLE dimoldb")
        if data:
            sql = (
                "INSERT INTO dimoldb (id, product_type, name, code, production_spec, "
                "km_mapping_code, length, width, height, remark, stock, created_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            )
            for item in data:
                cur.execute(
                    sql,
                    (
                        item.get("id", ""),
                        item.get("product_type", ""),
                        item.get("name", ""),
                        item.get("code", "") or "",
                        item.get("production_spec", "") or "",
                        item.get("km_mapping_code", "") or "",
                        item.get("length", 0),
                        item.get("width", 0),
                        item.get("height", 0),
                        item.get("remark", ""),
                        item.get("stock", 0),
                        item.get("created_at", ""),
                    ),
                )
        db.commit()
        cur.close()
        db.close()
        return True
    except Exception as e:
        print(f"[MySQL save_dimoldb] 错误: {e}")
        return False


def map_dimoldb_import_headers(headers: list[str]) -> dict[str, int]:
    """Excel 表头 → 字段列索引。"""
    col_map: dict[str, int] = {}
    for i, raw in enumerate(headers):
        h = str(raw or "").strip()
        hl = h.lower()
        if "名称" in h or h == "name":
            col_map["name"] = i
        elif "类型" in h or "产品" in h or "product" in hl:
            col_map["product_type"] = i
        elif "编码" in h or h == "code" or hl == "code":
            col_map["code"] = i
        elif "生产规格" in h or "production_spec" in hl:
            col_map["production_spec"] = i
        elif ("快麦" in h and "映射" in h) or "km_mapping" in hl or h == "快麦商品映射":
            col_map["km_mapping_code"] = i
        elif "备注" in h or "remark" in hl:
            col_map["remark"] = i
        elif "长" in h or "length" in hl:
            col_map["length"] = i
        elif "宽" in h or "width" in hl:
            col_map["width"] = i
        elif "高" in h or "height" in hl:
            col_map["height"] = i
    return col_map


def cell_str(row: tuple, idx: int | None) -> str:
    if idx is None or idx >= len(row) or row[idx] is None:
        return ""
    return str(row[idx]).strip()


def cell_float(row: tuple, idx: int | None) -> float:
    try:
        if idx is None or idx >= len(row) or row[idx] is None:
            return 0.0
        return float(row[idx])
    except (TypeError, ValueError):
        return 0.0
