# -*- coding: utf-8 -*-
"""刀模库 MySQL 读写与匹配逻辑（客服端 / 生产端共用）。"""
from __future__ import annotations

import re
import threading
import time
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


_dim_cache_lock = threading.Lock()
_dim_cache: dict[str, Any] = {"rows": [], "ts": 0.0}
_DIM_CACHE_TTL = float(__import__("os").getenv("DIMOLDB_CACHE_TTL_SEC", "120"))


def invalidate_dimoldb_cache() -> None:
    with _dim_cache_lock:
        _dim_cache["ts"] = 0.0


def load_dimoldb(get_db: Callable, *, force: bool = False) -> list[dict[str, Any]]:
    """全量读库；列表 API 请优先用 load_dimoldb_cached。"""
    now = time.time()
    with _dim_cache_lock:
        if (
            not force
            and _dim_cache["rows"]
            and now - float(_dim_cache["ts"] or 0) < _DIM_CACHE_TTL
        ):
            return list(_dim_cache["rows"])
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
        with _dim_cache_lock:
            _dim_cache["rows"] = result
            _dim_cache["ts"] = now
        return result
    except Exception as e:
        print(f"[MySQL load_dimoldb] 错误: {e}")
        return []


def load_dimoldb_cached(get_db: Callable, *, force: bool = False) -> list[dict[str, Any]]:
    return load_dimoldb(get_db, force=force)


def build_dim_match_index(
    rows: list[dict[str, Any]], *, tol: float = 0.1
) -> dict[tuple[str, float, float, float], list[dict[str, Any]]]:
    """按 (product_type, L, W, H) 建索引，供库存列表匹配刀模（避免每行全表扫描）。"""
    index: dict[tuple[str, float, float, float], list[dict[str, Any]]] = {}
    for d in rows:
        dl, dw, dh = effective_dims(d)
        if not (dl and dw and dh):
            continue
        pt = str(d.get("product_type") or "")
        key = (pt, round(float(dl), 1), round(float(dw), 1), round(float(dh), 1))
        index.setdefault(key, []).append(d)
    return index


def match_dimoldb_for_inventory_item(
    item: dict[str, Any],
    dm_index: dict[tuple[str, float, float, float], list[dict[str, Any]]],
    *,
    infer_fn,
) -> list[dict[str, Any]]:
    """库存行匹配刀模（与 get_inventory 原逻辑一致，走索引）。"""
    l, w, h = item.get("length"), item.get("width"), item.get("height")
    itype = item.get("product_type") or ""
    idim = item.get("dim_type") or ""
    if not (l and w and h and itype):
        return []
    try:
        lk = (
            itype,
            round(float(l), 1),
            round(float(w), 1),
            round(float(h), 1),
        )
    except (TypeError, ValueError):
        return []
    candidates = list(dm_index.get(lk, []))
    if idim == "outer":
        candidates = [
            d
            for d in candidates
            if "(外)" in d.get("name", "")
            or "外" in (d.get("remark") or "")
        ]
    elif idim == "inner":
        candidates = [
            d
            for d in candidates
            if "(内)" in d.get("name", "")
            or "内" in (d.get("remark") or "")
        ]
    elif not idim:
        iname = item.get("name", "")
        if iname.startswith("内径"):
            candidates = [
                d
                for d in candidates
                if "(内)" in d.get("name", "")
                or "内" in (d.get("remark") or "")
            ]
        else:
            candidates = [
                d
                for d in candidates
                if "(外)" in d.get("name", "")
                or "外" in (d.get("remark") or "")
            ]
    return [
        {
            "id": dm.get("id", ""),
            "name": dm.get("name", ""),
            "code": dm.get("code", "") or "",
            "remark": dm.get("remark", "") or "",
        }
        for dm in candidates
    ]


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


_INV_TYPE_MAP = {
    "zhengsquare": "zhengsquare",
    "juxing": "changfang",
    "daikou": "changfang",
    "koudi": "changfang",
    "shuangcha": "changfang",
    "qita": "changfang",
}


def _parse_dims_from_text(text: str) -> tuple[float | None, float | None, float | None]:
    """从 production_spec / remark 中解析「52.5×39.5×8.5」类尺寸。"""
    s = (text or "").strip()
    if not s:
        return None, None, None
    m = re.search(
        r"生产规格[\(（]?\s*([\d.]+)\s*[×xX\*\.]+\s*([\d.]+)\s*[×xX\*\.]+\s*([\d.]+)",
        s,
    )
    if m:
        return float(m.group(1)), float(m.group(2)), float(m.group(3))
    nums = re.findall(r"\d+\.?\d*", s.replace("×", " ").replace("x", " ").replace("*", " "))
    if len(nums) >= 3:
        try:
            return float(nums[0]), float(nums[1]), float(nums[2])
        except ValueError:
            pass
    return None, None, None


def effective_dims(dm: dict) -> tuple[float | None, float | None, float | None]:
    """刀模用于库存匹配的有效长宽高（库字段优先，否则解析 production_spec / remark）。"""
    try:
        l = float(dm.get("length") or 0)
        w = float(dm.get("width") or 0)
        h = float(dm.get("height") or 0)
        if l > 0 and w > 0 and h > 0:
            return l, w, h
    except (TypeError, ValueError):
        pass
    for field in ("production_spec", "remark"):
        pl, pw, ph = _parse_dims_from_text(str(dm.get(field) or ""))
        if pl and pw and ph:
            return pl, pw, ph
    return None, None, None


def infer_inner_outer(dm: dict) -> str:
    """
    内外径推断：dim_type > production_spec/remark 内外径关键词 > name 中 (内)/(外)。
    适配大虾导入：name 仅编号如 51398，内外径在 remark「内径-组合…」中。
    """
    dt = (dm.get("dim_type") or "").strip()
    if dt in ("inner", "outer"):
        return dt
    blob = " ".join(
        [
            str(dm.get("production_spec") or ""),
            str(dm.get("remark") or ""),
            str(dm.get("name") or ""),
        ]
    )
    if "内径" in blob or "(内)" in blob or "内" in (dm.get("name") or ""):
        return "inner"
    if "外径" in blob or "(外)" in blob:
        return "outer"
    return ""


def dim_type_stock_compatible(dm: dict, dm_dt: str, iv_dt: str) -> bool:
    """库存与刀模内外径是否可匹配（组合刀模、任一侧为空则放宽）。"""
    rk = str(dm.get("remark") or "")
    if "组合" in rk:
        return True
    if not dm_dt or not iv_dt:
        return True
    return dm_dt == iv_dt


def calc_dimoldb_stock(dm: dict, inv_items: list[dict], *, tol: float = 0.15) -> int:
    """按尺寸 + 内外径 + 产品类型汇总库存件数。"""
    dm_l, dm_w, dm_h = effective_dims(dm)
    if not (dm_l and dm_w and dm_h):
        return 0
    dm_dt = (dm.get("dim_type") or "").strip() or infer_inner_outer(dm)
    dm_type = dm.get("product_type", "")
    inv_type_map = _INV_TYPE_MAP.get(dm_type, dm_type)
    total = 0
    for iv in inv_items:
        try:
            iv_l = float(iv.get("length") or 0)
            iv_w = float(iv.get("width") or 0)
            iv_h = float(iv.get("height") or 0)
        except (TypeError, ValueError):
            continue
        if not (iv_l and iv_w and iv_h):
            continue
        if abs(iv_l - float(dm_l)) >= tol:
            continue
        if abs(iv_w - float(dm_w)) >= tol:
            continue
        if abs(iv_h - float(dm_h)) >= tol:
            continue
        iv_dt = (iv.get("dim_type") or "").strip()
        if not dim_type_stock_compatible(dm, dm_dt, iv_dt):
            continue
        iv_type = iv.get("product_type", "")
        if iv_type and iv_type != inv_type_map:
            continue
        total += int(iv.get("qty") or iv.get("stock") or 0)
    return total


def cell_float(row: tuple, idx: int | None) -> float:
    try:
        if idx is None or idx >= len(row) or row[idx] is None:
            return 0.0
        return float(row[idx])
    except (TypeError, ValueError):
        return 0.0
