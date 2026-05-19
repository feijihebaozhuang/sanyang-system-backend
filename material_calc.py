# -*- coding: utf-8 -*-
"""生产算料：报价英寸纸长/纸度 → raw_materials 匹配 → 开数 → 刀模。"""
from __future__ import annotations

import json
import math
import os
import re
import time
from typing import Any, Callable

import quote_calc_core as qcc

# 订单材质关键词 → raw_materials 行需同时包含的供应商/材质标记（按优先级）
MATERIAL_ROW_RULES: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
    (("P6D",), ("同舟", "P6D")),
    (("D6D", "特硬", "国产"), ("同舟", "D6D")),
    (("白色", "双白", "W7W"), ("锦丰", "白")),
    (("台湾", "进口"), ("龙成", "台湾")),
    (("黑色", "黑卡"), ("龙成", "黑")),
    (("红色",), ("龙成", "红")),
    (("EB", "五层EB", "5层"), ("新浦", "EB")),
    (("BC", "五层BC"), ("新浦", "BC")),
    (("B坑", "B瓦", "三层", "3层"), ("新浦", "B")),
]

MAX_REMAINDER_INCH = 1.0

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


def _to_inch(val: float) -> float:
    """库内数值：≤120 视为英寸；更大视为厘米并换算。"""
    if val <= 0:
        return 0.0
    if val > 120:
        return val / 2.54
    return val


def _paper_dims_inch(row: dict) -> tuple[float, float]:
    """paper_width=纸度(英寸), paper_length=纸长(英寸)。"""
    pw = _to_inch(_float_val(row.get("paper_width")))
    pl = _to_inch(_float_val(row.get("paper_length")))
    if pw > 0 and pl > 0 and pw > pl * 3:
        pw, pl = pl, pw
    return pw, pl


def _row_blob(row: dict) -> str:
    return f"{row.get('supplier','')} {row.get('name','')} {row.get('remark','')}"


def row_matches_material(row: dict, material_text: str) -> bool:
    if not material_text:
        return True
    t = material_text.upper()
    blob = _row_blob(row).upper()
    for order_kws, row_kws in MATERIAL_ROW_RULES:
        if any(kw.upper() in t for kw in order_kws):
            return all(rk.upper() in blob for rk in row_kws)
    return any(
        k.upper() in blob
        for k in re.split(r"[\s,，/、]+", material_text)
        if len(k) >= 2
    )


def _leftover_inch(stock: float, need: float) -> float | None:
    """开数≥1 且余料≤1英寸；否则该规格不可用。"""
    if need <= 0 or stock < need:
        return None
    n = int(stock // need)
    if n < 1:
        return None
    rem = stock - n * need
    if rem > MAX_REMAINDER_INCH:
        return None
    return rem


def match_paper(
    paper_l_inch: float,
    paper_w_inch: float,
    material_text: str,
    raw_rows: list[dict],
    *,
    prefer_stock: bool = True,
) -> dict[str, Any]:
    """
    按英寸匹配纸板：纸度≥paper_w_inch、纸长≥paper_l_inch，余料≤1英寸，选浪费最小。
    优先 qty>0；无库存则退而求其次。
    """
    need_l = float(paper_l_inch)
    need_w = float(paper_w_inch)
    if need_l <= 0 or need_w <= 0:
        return {"success": False, "error": "纸长/纸度英寸无效", "shortage": True}

    def _scan(rows: list[dict]) -> list[dict]:
        out: list[dict] = []
        for row in rows:
            if not row_matches_material(row, material_text):
                continue
            pw, pl = _paper_dims_inch(row)
            rem_w = _leftover_inch(pw, need_w)
            rem_l = _leftover_inch(pl, need_l)
            if rem_w is None or rem_l is None:
                continue
            cuts_w = int(pw // need_w)
            cuts_l = int(pl // need_l)
            per_board = cuts_w * cuts_l
            if per_board < 1:
                continue
            waste = rem_w + rem_l
            out.append(
                {
                    "row": row,
                    "paper_width_inch": pw,
                    "paper_length_inch": pl,
                    "waste": waste,
                    "area": pw * pl,
                    "cuts_w": cuts_w,
                    "cuts_l": cuts_l,
                    "per_board": per_board,
                    "qty_on_hand": int(row.get("qty") or 0),
                }
            )
        return out

    stocked = [r for r in raw_rows if int(r.get("qty") or 0) > 0]
    candidates = _scan(stocked if prefer_stock and stocked else raw_rows)
    if not candidates and prefer_stock and stocked:
        candidates = _scan(raw_rows)

    if not candidates:
        return {
            "success": False,
            "shortage": True,
            "error": "缺料：未找到合适纸板规格，请员工自行决定",
            "paper_l_inch": need_l,
            "paper_w_inch": need_w,
            "material": material_text,
        }

    best = min(candidates, key=lambda x: (x["waste"], x["area"], -x["qty_on_hand"]))
    r = best["row"]
    return {
        "success": True,
        "supplier": r.get("supplier") or "",
        "name": r.get("name") or "",
        "paper_spec": f"{best['paper_width_inch']}×{best['paper_length_inch']}英寸",
        "paper_width_inch": best["paper_width_inch"],
        "paper_length_inch": best["paper_length_inch"],
        "cuts_width": best["cuts_w"],
        "cuts_length": best["cuts_l"],
        "sheets_per_board": best["per_board"],
        "qty_on_hand": best["qty_on_hand"],
        "waste_inch": round(best["waste"], 2),
        "material": material_text,
        "has_stock": best["qty_on_hand"] > 0,
    }


def match_dimoldb(
    length: float,
    width: float,
    height: float,
    dimoldb: list[dict],
    product_type: str = "",
    tol: float = 0.6,
) -> dict[str, Any]:
    del product_type
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
        if ot == "飞机盒" and ("带扣" in a or "扣" in a):
            return "带扣"
        return ot
    if "扣底" in a:
        return "扣底盒"
    if "双插" in a:
        return "双插盒"
    if "纸箱" in a:
        return "纸箱"
    if "飞机盒" in a or ot == "飞机盒":
        return "带扣" if "带扣" in a or "扣" in a else "飞机盒"
    return "飞机盒"


def calc_sheets_per_board(
    paper_l_inch: float,
    paper_w_inch: float,
    stock_l_inch: float,
    stock_w_inch: float,
) -> int:
    if paper_l_inch <= 0 or paper_w_inch <= 0:
        return 0
    return int(stock_w_inch // paper_w_inch) * int(stock_l_inch // paper_l_inch)


def load_raw_rows(load_raw_fn: Callable[[], list[dict]], *, max_age: int = 120) -> list[dict]:
    global _raw_cache
    now = time.time()
    if _raw_cache.get("rows") and now - float(_raw_cache.get("ts") or 0) < max_age:
        return _raw_cache["rows"]
    rows = load_raw_fn() or []
    _raw_cache = {"ts": now, "rows": rows}
    return rows


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
    calc_pt = pt
    if pt == "纸箱":
        calc_pt = "纸箱"
    elif pt == "扣底盒":
        calc_pt = "扣底盒"
    elif pt == "双插盒":
        calc_pt = "双插盒"
    else:
        calc_pt = "飞机盒"

    mat_key = resolve_material_key(material_text, quote_data)
    inches = qcc.calc_paper_inches(
        calc_pt,
        l,
        w,
        h,
        quote_data=quote_data,
        is_buckle=is_buckle,
        material_key=mat_key,
    )
    paper_l_inch = inches["paper_l_inch"]
    paper_w_inch = inches["paper_w_inch"]

    paper = match_paper(paper_l_inch, paper_w_inch, material_text, raw_rows)
    if not paper.get("success"):
        return {
            "status": "shortage" if paper.get("shortage") else "error",
            "material_status": "shortage" if paper.get("shortage") else "error",
            "error": paper.get("error", "纸板匹配失败"),
            "paper_l_inch": paper_l_inch,
            "paper_w_inch": paper_w_inch,
            "inches": inches,
            "material": material_text,
            "attrs": attrs,
        }

    per_board = paper.get("sheets_per_board") or calc_sheets_per_board(
        paper_l_inch,
        paper_w_inch,
        paper["paper_length_inch"],
        paper["paper_width_inch"],
    )
    if per_board <= 0:
        return {
            "status": "error",
            "error": "纸板尺寸不足以开料（每张裁0个）",
            "paper_l_inch": paper_l_inch,
            "paper_w_inch": paper_w_inch,
            "paper": paper,
        }

    need_boards = int(math.ceil(qty / per_board * 1.02)) if qty else 0
    dm = match_dimoldb(l, w, h, dimoldb, pt)
    spec_label = f"{paper.get('supplier')} - {paper.get('name')} - {paper.get('paper_spec')}"

    return {
        "status": "done",
        "material_status": "done",
        "attrs": attrs,
        "qty": qty,
        "material": material_text or mat_key,
        "material_key": mat_key,
        "product_type": calc_pt,
        "inches": inches,
        "paper_l_inch": paper_l_inch,
        "paper_w_inch": paper_w_inch,
        "paper": paper,
        "paper_display": spec_label,
        "paper_spec": spec_label,
        "boards_needed": need_boards,
        "sheets_per_board": per_board,
        "cuts_width": paper.get("cuts_width"),
        "cuts_length": paper.get("cuts_length"),
        "dimoldb": dm,
        "dimoldb_id": dm.get("dimoldb_id") if dm.get("success") else "",
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
