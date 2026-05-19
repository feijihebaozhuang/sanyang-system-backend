# -*- coding: utf-8 -*-
"""生产算料：展开尺寸、纸板匹配、刀模匹配。"""
from __future__ import annotations

import json
import math
import os
import re
import time
from typing import Any, Callable

import quote_calc_core as qcc

# 材质关键词 → 优先供应商（名称包含即可）
MATERIAL_SUPPLIER_HINTS: list[tuple[str, list[str]]] = [
    ("台湾", ["龙成", "锦丰"]),
    ("进口", ["龙成", "锦丰"]),
    ("D6D", ["同舟", "新浦", "龙成"]),
    ("P6D", ["同舟", "新浦"]),
    ("特硬", ["同舟", "新浦", "龙成"]),
    ("国产", ["同舟", "新浦"]),
    ("双白", ["同舟", "新浦", "龙成"]),
    ("白色", ["同舟", "新浦", "龙成"]),
    ("EB", ["同舟", "新浦"]),
    ("BC", ["同舟", "新浦"]),
    ("B坑", ["同舟", "新浦"]),
    ("E坑", ["同舟", "新浦"]),
]

_raw_cache: dict[str, Any] = {"ts": 0, "rows": []}
_calc_cache: dict[str, dict] = {}
_CALC_FILE = os.path.join(os.path.dirname(__file__), "material_calc_cache.json")


def _float_val(v: Any) -> float:
    if v is None or v == "":
        return 0.0
    try:
        s = str(v).strip().replace("×", "x").replace("X", "x")
        m = re.search(r"(\d+(?:\.\d+)?)", s)
        return float(m.group(1)) if m else 0.0
    except (TypeError, ValueError):
        return 0.0


def _paper_size_cm(row: dict) -> tuple[float, float]:
    """纸度×纸长 → (width_cm, length_cm)。"""
    pw = _float_val(row.get("paper_width"))
    pl = _float_val(row.get("paper_length"))
    if pl > 500:
        pl = pl / 10.0
    if pw > 500:
        pw = pw / 10.0
    if pl > 0 and pl < 50 and pw > pl * 2:
        pw, pl = pl, pw
    return pw, pl


def load_raw_rows(load_raw_fn: Callable[[], list[dict]], *, max_age: int = 120) -> list[dict]:
    global _raw_cache
    now = time.time()
    if _raw_cache.get("rows") and now - float(_raw_cache.get("ts") or 0) < max_age:
        return _raw_cache["rows"]
    rows = load_raw_fn() or []
    _raw_cache = {"ts": now, "rows": rows}
    return rows


def supplier_hints_for_material(material_text: str) -> list[str]:
    t = (material_text or "").strip()
    hints: list[str] = []
    for kw, sups in MATERIAL_SUPPLIER_HINTS:
        if kw in t:
            hints.extend(sups)
    seen: set[str] = set()
    out: list[str] = []
    for s in hints:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def row_matches_material(row: dict, material_text: str) -> bool:
    blob = f"{row.get('name','')} {row.get('remark','')} {row.get('supplier','')}"
    if not material_text:
        return True
    t = material_text.lower()
    for kw, _ in MATERIAL_SUPPLIER_HINTS:
        if kw.lower() in t and kw in blob:
            return True
    return any(k in blob for k in re.split(r"[\s,，/、]+", material_text) if len(k) >= 2)


def match_paper(
    spread_l_cm: float,
    spread_w_cm: float,
    material_text: str,
    raw_rows: list[dict],
) -> dict[str, Any]:
    """匹配最小可用纸板规格。"""
    need_l = float(spread_l_cm)
    need_w = float(spread_w_cm)
    if need_l <= 0 or need_w <= 0:
        return {"success": False, "error": "展开尺寸无效"}

    candidates: list[dict] = []
    for row in raw_rows:
        if not row_matches_material(row, material_text):
            continue
        pw, pl = _paper_size_cm(row)
        if pw >= need_w and pl >= need_l:
            candidates.append(
                {
                    "row": row,
                    "paper_width_cm": pw,
                    "paper_length_cm": pl,
                    "area": pw * pl,
                }
            )
    if not candidates:
        return {
            "success": False,
            "error": "未找到满足尺寸的纸板（请检查材质与 raw_materials 数据）",
            "need_l_cm": need_l,
            "need_w_cm": need_w,
            "material": material_text,
        }
    best = min(candidates, key=lambda x: x["area"])
    r = best["row"]
    return {
        "success": True,
        "supplier": r.get("supplier") or "",
        "name": r.get("name") or "",
        "paper_spec": f"{best['paper_width_cm']}×{best['paper_length_cm']}cm",
        "paper_width_cm": best["paper_width_cm"],
        "paper_length_cm": best["paper_length_cm"],
        "qty_on_hand": int(r.get("qty") or 0),
        "material": material_text,
    }


def match_dimoldb(
    length: float,
    width: float,
    height: float,
    dimoldb: list[dict],
    product_type: str = "",
    tol: float = 0.6,
) -> dict[str, Any]:
    best = None
    for dm in dimoldb:
        try:
            dl = float(dm.get("length") or 0)
            dw = float(dm.get("width") or 0)
            dh = float(dm.get("height") or 0)
        except (TypeError, ValueError):
            continue
        if abs(dl - length) > tol or abs(dw - width) > tol:
            continue
        if height > 0 and dh > 0 and abs(dh - height) > tol:
            continue
        best = dm
        break
    if not best:
        return {"success": False, "error": "未匹配到刀模"}
    return {
        "success": True,
        "dimoldb_id": best.get("id"),
        "code": best.get("code") or "",
        "name": best.get("name") or "",
    }


def resolve_material_key(material_text: str, quote_data: dict) -> str:
    t = (material_text or "").strip()
    mapping = quote_data.get("material_mapping") or []
    for row in mapping:
        kws = (row.get("keywords") or "").split(",")
        for kw in kws:
            kw = kw.strip()
            if kw and kw in t:
                return row.get("material_key") or "d6d"
    if "台湾" in t or "进口" in t:
        return "taiwan"
    if "P6D" in t.upper():
        return "p6d"
    if "EB" in t.upper():
        return "eb_keng"
    if "BC" in t.upper():
        return "bc_keng"
    if "B坑" in t or "B瓦" in t:
        return "b_keng"
    return "d6d"


def infer_product_type_for_calc(order_type: str, attrs: str) -> str:
    ot = (order_type or "").strip()
    a = attrs or ""
    if ot in ("扣底盒", "双插盒", "纸箱", "带扣", "飞机盒"):
        if ot == "飞机盒" and ("带扣" in a or "扣" in ot):
            return "带扣"
        return ot
    if "扣底" in a or "双插" in ot:
        return "扣底盒" if "扣底" in a else "双插盒"
    if "纸箱" in a:
        return "纸箱"
    if "飞机盒" in a or ot == "飞机盒":
        return "带扣" if "带扣" in a or "扣" in a else "飞机盒"
    return "飞机盒"


def calc_sheets_per_board(spread_l_cm: float, spread_w_cm: float, paper_l_cm: float, paper_w_cm: float) -> int:
    if spread_l_cm <= 0 or spread_w_cm <= 0 or paper_l_cm <= 0 or paper_w_cm <= 0:
        return 0
    nx = max(0, int(paper_l_cm // spread_l_cm))
    ny = max(0, int(paper_w_cm // spread_w_cm))
    return max(nx * ny, 0)


def calc_material_line(
    *,
    attrs: str,
    qty: int,
    order_type: str,
    material_text: str,
    quote_data: dict,
    raw_rows: list[dict],
    dimoldb: list[dict],
) -> dict[str, Any]:
    lwh = _parse_lwh_from_attrs(attrs)
    if not lwh:
        return {"status": "error", "error": "无法从规格解析长宽高", "attrs": attrs}
    l, w, h = lwh
    pt = infer_product_type_for_calc(order_type, attrs)
    is_buckle = pt in ("带扣", "daikou")
    if pt == "纸箱":
        calc_pt = "纸箱"
    elif pt == "扣底盒":
        calc_pt = "扣底盒"
    elif pt == "双插盒":
        calc_pt = "双插盒"
    else:
        calc_pt = "飞机盒"

    expand = qcc.expand_dimensions(
        calc_pt, l, w, h, quote_data=quote_data, is_buckle=is_buckle or pt == "带扣"
    )
    spread_l = expand["spread_l_cm"]
    spread_w = expand["spread_w_cm"]
    mat_key = resolve_material_key(material_text, quote_data)
    paper = match_paper(spread_l, spread_w, material_text, raw_rows)
    if not paper.get("success"):
        return {
            "status": "error",
            "error": paper.get("error", "纸板匹配失败"),
            "expand": expand,
            "material": material_text,
            "attrs": attrs,
        }

    per_board = calc_sheets_per_board(
        spread_l, spread_w, paper["paper_length_cm"], paper["paper_width_cm"]
    )
    if per_board <= 0:
        return {
            "status": "error",
            "error": "纸板尺寸不足以开料（每张裁0个）",
            "expand": expand,
            "paper": paper,
        }
    need_boards = int(math.ceil(qty / per_board * 1.02)) if qty else 0
    dm = match_dimoldb(l, w, h, dimoldb, pt)

    return {
        "status": "done",
        "attrs": attrs,
        "qty": qty,
        "material": material_text or mat_key,
        "material_key": mat_key,
        "product_type": calc_pt,
        "expand": expand,
        "spread_l_cm": spread_l,
        "spread_w_cm": spread_w,
        "paper": paper,
        "paper_display": f"{paper.get('supplier')} - {paper.get('name')} - {paper.get('paper_spec')}",
        "sheets_per_board": per_board,
        "boards_needed": need_boards,
        "dimoldb": dm,
        "dimoldb_code": dm.get("code") if dm.get("success") else "",
        "dimoldb_name": dm.get("name") if dm.get("success") else "",
    }


def _parse_lwh_from_attrs(attrs: str) -> tuple[float, float, float] | None:
    try:
        import production_spec as pspec

        dims = pspec._parse_dimensions(attrs or "")
        if dims.get("l") and dims.get("w") and dims.get("h"):
            return float(dims["l"]), float(dims["w"]), float(dims["h"])
        if dims.get("l") and dims.get("w"):
            return float(dims["l"]), float(dims["w"]), float(dims.get("h") or 0)
    except Exception:
        pass
    m3 = re.search(
        r"(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)\s*[*×xX]\s*(\d+(?:\.\d+)?)",
        attrs or "",
    )
    if m3:
        return float(m3.group(1)), float(m3.group(2)), float(m3.group(3))
    return None


def load_calc_cache() -> dict:
    global _calc_cache
    if _calc_cache:
        return _calc_cache
    if os.path.exists(_CALC_FILE):
        try:
            with open(_CALC_FILE, "r", encoding="utf-8") as f:
                _calc_cache = json.load(f)
        except Exception:
            _calc_cache = {}
    else:
        _calc_cache = {}
    return _calc_cache


def save_calc_cache(data: dict) -> None:
    global _calc_cache
    _calc_cache = data
    try:
        with open(_CALC_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[material_calc_cache] 保存失败: {e}")


def cache_key(so_id: str, line_index: int) -> str:
    return f"{so_id}#{line_index}"


def get_cached_line(so_id: str, line_index: int) -> dict | None:
    return load_calc_cache().get(cache_key(so_id, line_index))


def set_cached_line(so_id: str, line_index: int, result: dict) -> None:
    data = load_calc_cache()
    data[cache_key(so_id, line_index)] = {
        **result,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_calc_cache(data)
