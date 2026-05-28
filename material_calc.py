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

# 飞机盒/扣底等 E坑（同舟/锦丰/龙成）
E_PIT_ROW_RULES: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
    (("P6D",), ("同舟", "P6D")),
    (("D6D", "特硬", "国产"), ("同舟", "D6D")),
    (("白色", "双白", "W7W"), ("锦丰", "白")),
    (("台湾", "进口"), ("龙成", "台湾")),
    (("黑色", "黑卡"), ("龙成", "黑")),
    (("红色",), ("龙成", "红")),
]

# 纸箱仅新浦 B/EB 坑（不与 E坑 红色等混用）
CARTON_ROW_RULES: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
    (("EB", "五层EB", "5层EB"), ("新浦", "EB")),
    (("BC", "五层BC"), ("新浦", "BC")),
    (("B坑", "B瓦", "三层", "3层", "3层B", "B楞"), ("新浦", "B")),
]

E_PIT_SUPPLIERS = ("同舟", "锦丰", "龙成")
CARTON_SUPPLIERS = ("新浦",)
# 纸箱原材料扫描时排除 E 坑平盒类库存（仅保留新浦 B/EB/BC 坑纸）
_CARTON_EXCLUDE_ROW_MARKERS = (
    "同舟",
    "龙成",
    "锦丰",
    "E坑",
    "E瓦",
    "P6D",
    "D6D",
    "特硬",
)

MAX_REMAINDER_INCH = 1.0
# 纸箱大板：余料 <5cm 或 >25cm 才可用（5~25cm 视为浪费）；度/长优先试开4→3→2→1
CARTON_REM_OK_LT_CM = 5.0
CARTON_REM_OK_GT_CM = 25.0
CARTON_CUT_TRY_ORDER = (4, 3, 2, 1)

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
    if val <= 0:
        return 0.0
    if val > 120:
        return val / 2.54
    return val


def _paper_dims_inch(row: dict) -> tuple[float, float]:
    pw = _to_inch(_float_val(row.get("paper_width")))
    pl = _to_inch(_float_val(row.get("paper_length")))
    if pw > 0 and pl > 0 and pw > pl * 3:
        pw, pl = pl, pw
    return pw, pl


def _row_blob(row: dict) -> str:
    return f"{row.get('supplier','')} {row.get('name','')} {row.get('remark','')}"


def _is_carton_product(product_type: str, attrs: str = "") -> bool:
    import production_spec as pspec

    pt = (product_type or "").strip()
    if pt in ("纸箱", "qita"):
        return True
    if pspec.attrs_indicate_carton(attrs or ""):
        return True
    return False


def _material_rules(product_type: str, attrs: str) -> list[tuple[tuple[str, ...], tuple[str, ...]]]:
    if _is_carton_product(product_type, attrs):
        return CARTON_ROW_RULES
    return E_PIT_ROW_RULES


def _row_excluded_for_carton(blob: str) -> bool:
    """纸箱订单跳过 E 坑/同舟/龙成等平盒纸板行。"""
    return any(m in blob for m in _CARTON_EXCLUDE_ROW_MARKERS)


def _supplier_allowed(blob: str, product_type: str, attrs: str) -> bool:
    if _is_carton_product(product_type, attrs):
        return any(s in blob for s in CARTON_SUPPLIERS)
    return any(s in blob for s in E_PIT_SUPPLIERS)


def row_matches_material(
    row: dict,
    material_text: str,
    *,
    product_type: str = "",
    attrs: str = "",
) -> bool:
    blob = _row_blob(row)
    if not _supplier_allowed(blob, product_type, attrs):
        return False
    if not material_text:
        return True
    t = material_text.upper()
    blob_u = blob.upper()
    rules = _material_rules(product_type, attrs)
    for order_kws, row_kws in rules:
        if any(kw.upper() in t for kw in order_kws):
            return all(rk.upper() in blob_u for rk in row_kws)
    if _is_carton_product(product_type, attrs):
        return False
    return any(
        k.upper() in blob_u
        for k in re.split(r"[\s,，/、]+", material_text)
        if len(k) >= 2
    )


def _inch_disp(v: float) -> str:
    r = round(float(v), 2)
    if abs(r - round(r)) < 1e-6:
        return str(int(round(r)))
    return f"{r:.2f}".rstrip("0").rstrip(".")


def _cm_disp(v: float) -> str:
    r = round(float(v), 2)
    if abs(r - round(r)) < 1e-6:
        return str(int(round(r)))
    return f"{r:.2f}".rstrip("0").rstrip(".")


def _rem_disp_cm(rem_cm: float) -> str:
    """余料展示：<5cm 写「略」，否则写厘米数。"""
    if float(rem_cm) < CARTON_REM_OK_LT_CM:
        return "略"
    return f"{_cm_disp(rem_cm)}cm"


def format_paper_shortage_message(
    *,
    product_label: str,
    length_cm: float,
    width_cm: float,
    height_cm: float,
    paper_l_inch: float,
    paper_w_inch: float,
) -> str:
    """统一缺料文案：仅订单尺寸(cm) + 展开纸长/纸度(英寸)，不展示库存纸板规格。"""
    pt = (product_label or "产品").strip()
    size = (
        f"{_cm_disp(length_cm)}×{_cm_disp(width_cm)}×{_cm_disp(height_cm)}"
    )
    pl = _inch_disp(paper_l_inch)
    pw = _inch_disp(paper_w_inch)
    return (
        f"缺料：{pt} {size}cm，展开需纸长{pl}英寸×纸度{pw}英寸"
    )


def _find_nearest_paper_row(
    need_l: float,
    need_w: float,
    material_text: str,
    raw_rows: list[dict],
    *,
    product_type: str = "",
    attrs: str = "",
) -> dict[str, Any] | None:
    """无库存可开料时，找材料匹配且尺寸最接近的纸板行（仅作调试/扩展，不写入缺料文案）。"""
    best: dict[str, Any] | None = None
    best_gap = 1e9
    for row in raw_rows or []:
        blob = _row_blob(row)
        if _is_carton_product(product_type, attrs) and _row_excluded_for_carton(blob):
            continue
        if not row_matches_material(
            row, material_text, product_type=product_type, attrs=attrs
        ):
            continue
        pw, pl = _paper_dims_inch(row)
        if pw <= 0 or pl <= 0:
            continue
        gap_w = max(0.0, need_w - pw)
        gap_l = max(0.0, need_l - pl)
        gap = gap_w + gap_l
        if gap < best_gap:
            best_gap = gap
            best = row
    return best


def _leftover_inch(stock: float, need: float) -> float | None:
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
    product_type: str = "",
    attrs: str = "",
    prefer_stock: bool = True,
    shortage_label: str = "",
    box_l_cm: float = 0,
    box_w_cm: float = 0,
    box_h_cm: float = 0,
) -> dict[str, Any]:
    need_l = float(paper_l_inch)
    need_w = float(paper_w_inch)
    if need_l <= 0 or need_w <= 0:
        return {"success": False, "error": "纸长/纸度英寸无效", "shortage": True}

    def _scan(rows: list[dict]) -> list[dict]:
        out: list[dict] = []
        for row in rows:
            blob = _row_blob(row)
            if _is_carton_product(product_type, attrs) and _row_excluded_for_carton(blob):
                continue
            if not row_matches_material(
                row, material_text, product_type=product_type, attrs=attrs
            ):
                continue
            pw, pl = _paper_dims_inch(row)
            if _is_carton_product(product_type, attrs):
                layout = _calc_cut_layout(pw, pl, need_w, need_l)
                if not layout:
                    continue
                cuts_w = layout["cuts_width"]
                cuts_l = layout["cuts_length"]
                per_board = layout["sheets_per_board"]
                waste = layout["waste_inch"]
            else:
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
        near_row = _find_nearest_paper_row(
            need_l,
            need_w,
            material_text,
            raw_rows,
            product_type=product_type,
            attrs=attrs,
        )
        err = format_paper_shortage_message(
            product_label=shortage_label or product_type or "产品",
            length_cm=box_l_cm,
            width_cm=box_w_cm,
            height_cm=box_h_cm,
            paper_l_inch=need_l,
            paper_w_inch=need_w,
        )
        return {
            "success": False,
            "shortage": True,
            "error": err,
            "shortage_detail": err,
            "nearest_paper": near_row,
            "paper_l_inch": need_l,
            "paper_w_inch": need_w,
            "material": material_text,
        }

    if _is_carton_product(product_type, attrs):
        best = min(
            candidates,
            key=lambda x: (
                -x["per_board"],
                -max(x["cuts_w"], x["cuts_l"]),
                x["waste"],
                x["area"],
                -x["qty_on_hand"],
            ),
        )
    else:
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


def _carton_material_text_from_suffix(mat_suffix: str) -> str:
    s = (mat_suffix or "").strip().upper()
    if "EB" in s:
        return "五层EB K636K"
    if "BC" in s:
        return "五层BC K737K"
    return "B坑 三层 K7K"


def _layer_short_label(mat_suffix: str) -> str:
    s = (mat_suffix or "").strip().upper()
    if "EB" in s or "BC" in s:
        return "5层"
    return "3层"


def _remainder_ok_cm(rem_cm: float) -> bool:
    """余料可用：小于 5cm，或大于 25cm（中间区间视为浪费）。 """
    return rem_cm < CARTON_REM_OK_LT_CM or rem_cm > CARTON_REM_OK_GT_CM


def _cuts_one_axis(stock_inch: float, need_inch: float) -> tuple[int, float] | None:
    """单方向开数：先试开4，不行 3→2→1，且余料须满足 _remainder_ok_cm。"""
    if need_inch <= 0 or stock_inch < need_inch:
        return None
    max_n = int(stock_inch // need_inch)
    for target in CARTON_CUT_TRY_ORDER:
        if target > max_n:
            continue
        rem_cm = (stock_inch - target * need_inch) * 2.54
        if _remainder_ok_cm(rem_cm):
            return target, rem_cm
    return None


def _calc_cut_layout(
    stock_w: float, stock_l: float, need_w: float, need_l: float
) -> dict[str, Any] | None:
    """纸箱大板开料：度=need_w，长=need_l；开数 4→3→2→1，余料 <5cm 或 >25cm。"""
    w_axis = _cuts_one_axis(stock_w, need_w)
    l_axis = _cuts_one_axis(stock_l, need_l)
    if not w_axis or not l_axis:
        return None
    cuts_w, rem_w_cm = w_axis
    cuts_l, rem_l_cm = l_axis
    rem_w_inch = rem_w_cm / 2.54
    rem_l_inch = rem_l_cm / 2.54
    return {
        "cuts_width": cuts_w,
        "cuts_length": cuts_l,
        "rem_w_cm": rem_w_cm,
        "rem_l_cm": rem_l_cm,
        "waste_inch": rem_w_inch + rem_l_inch,
        "sheets_per_board": cuts_w * cuts_l,
    }


def _best_carton_board_layout(
    paper_l_inch: float,
    paper_w_inch: float,
    material_text: str,
    raw_rows: list[dict],
) -> dict[str, Any] | None:
    """与 match_paper 同规则；无库存时也选最优大板（开数优先、余料合规）。"""
    need_l, need_w = float(paper_l_inch), float(paper_w_inch)
    best: dict[str, Any] | None = None
    for row in raw_rows or []:
        blob = _row_blob(row)
        if _row_excluded_for_carton(blob):
            continue
        if not row_matches_material(
            row, material_text, product_type="纸箱", attrs=material_text
        ):
            continue
        pw, pl = _paper_dims_inch(row)
        layout = _calc_cut_layout(pw, pl, need_w, need_l)
        if not layout:
            continue
        item = {
            **layout,
            "paper_width_inch": pw,
            "paper_length_inch": pl,
            "qty_on_hand": int(row.get("qty") or 0),
        }
        key = (
            -item["sheets_per_board"],
            -max(layout["cuts_width"], layout["cuts_length"]),
            item["waste_inch"],
            pw * pl,
            -item["qty_on_hand"],
        )
        if best is None or key < best["_sort_key"]:
            item["_sort_key"] = key
            best = item
    if best:
        best.pop("_sort_key", None)
    return best


def format_carton_kuaimai_exec_std(
    *,
    mat_suffix: str,
    paper_w_inch: float,
    paper_l_inch: float,
    bu_tag: str = "(单卜)",
    raw_rows: list[dict] | None = None,
) -> str:
    """
    快麦执行标准（主管格式）：
    3层 单卜10*10英寸 31度开3 余0cm 66长开6 余15cm
    """
    layer = _layer_short_label(mat_suffix)
    bu = (bu_tag or "").strip().strip("()") or "单卜"
    head = (
        f"{layer} {bu}{_inch_disp(paper_w_inch)}*{_inch_disp(paper_l_inch)}英寸"
    )
    mat_text = _carton_material_text_from_suffix(mat_suffix)
    rows = raw_rows or []

    board: dict[str, Any] | None = None
    matched = match_paper(
        paper_l_inch,
        paper_w_inch,
        mat_text,
        rows,
        product_type="纸箱",
        attrs=mat_text,
        prefer_stock=True,
        shortage_label="纸箱",
    )
    if matched.get("success"):
        layout = _calc_cut_layout(
            float(matched["paper_width_inch"]),
            float(matched["paper_length_inch"]),
            float(paper_w_inch),
            float(paper_l_inch),
        )
        if layout:
            board = {**matched, **layout}

    if not board:
        board = _best_carton_board_layout(
            paper_l_inch, paper_w_inch, mat_text, rows
        )

    if not board:
        return head

    sw = _inch_disp(board["paper_width_inch"])
    sl = _inch_disp(board["paper_length_inch"])
    cw = int(board["cuts_width"])
    cl = int(board["cuts_length"])
    return (
        f"{head} {sw}度开{cw} 余{_rem_disp_cm(board['rem_w_cm'])} "
        f"{sl}长开{cl} 余{_rem_disp_cm(board['rem_l_cm'])}"
    )


def dimoldb_display_code(dm: dict | None) -> str:
    """刀模展示编码：优先 code，其次 id；name 若为尺寸串（含 *×）则不用于编码。"""
    if not dm:
        return ""
    code = str(dm.get("code") or "").strip()
    if code:
        return code
    rid = str(dm.get("id") or "").strip()
    name = str(dm.get("name") or "").strip()
    if name and not re.search(r"\d+(?:\.\d+)?\s*[*×xX]\s*\d+", name):
        return name
    return rid


def match_dimoldb(
    length: float,
    width: float,
    height: float,
    dimoldb: list[dict],
    product_type: str = "",
    tol: float | None = None,
    *,
    diameter_type: str = "",
) -> dict[str, Any]:
    import dimoldb_store as ds
    import hardcoded_config as hc

    if tol is None:
        tol = hc.DIMOLD_MATCH_TOLERANCE_CM
    pt = (product_type or "").strip()
    if pt == "纸箱" or _is_carton_product(pt):
        return {
            "success": False,
            "skip": True,
            "error": "纸箱无需刀模",
            "dimoldb_id": "",
            "code": "",
            "name": "",
        }
    best = ds.find_best_dimoldb_match(
        float(length),
        float(width),
        float(height or 0),
        dimoldb or [],
        product_type=pt,
        diameter_type=diameter_type or "",
        tol=tol,
    )
    if not best:
        return {"success": False, "error": "未匹配到刀模"}
    display_code = dimoldb_display_code(best)
    return {
        "success": True,
        "dimoldb_id": best.get("id"),
        "code": display_code,
        "name": best.get("name") or "",
        "display_code": display_code,
        "row": best,
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
    if "B坑" in t or "B瓦" in t or "三层" in t:
        return "b_keng"
    return "d6d"


def infer_product_type_for_calc(order_type: str, attrs: str) -> str:
    import production_spec as pspec

    ot = (order_type or "").strip()
    a = attrs or ""
    if pspec.attrs_indicate_carton(a):
        return "纸箱"
    if "纸箱" in a and "飞机盒" not in a:
        return "纸箱"
    if ot in ("扣底盒", "双插盒", "纸箱", "带扣", "飞机盒"):
        if ot == "飞机盒" and ("带扣" in a):
            return "带扣"
        return ot
    if "扣底" in a:
        return "扣底盒"
    if "双插" in a:
        return "双插盒"
    if "纸箱" in a:
        return "纸箱"
    if "飞机盒" in a or ot == "飞机盒":
        return "带扣" if "带扣" in a else "飞机盒"
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


def _parse_lwh_from_attrs(attrs: str, *, title: str = "") -> tuple[float, float, float] | None:
    import production_spec as pspec

    dims = pspec.parse_dimensions_for_item(attrs or "", title or "")
    if not pspec.dimensions_ready_for_calc(dims):
        return None
    return float(dims["l"]), float(dims["w"]), float(dims["h"])


def calc_material_line(
    *,
    attrs: str,
    qty: int,
    order_type: str,
    material_text: str,
    quote_data: dict,
    raw_rows: list[dict],
    dimoldb: list[dict],
    title: str = "",
    prebuilt_ps: dict[str, Any] | None = None,
    sku: str = "",
) -> dict[str, Any]:
    import production_spec as pspec

    raw_attrs = (attrs or "").strip()
    clean_attrs = pspec.sanitize_sku_attrs(raw_attrs) or raw_attrs
    mat_map = quote_data.get("material_mapping") or []
    if prebuilt_ps and prebuilt_ps.get("km_dims_missing"):
        return {
            "status": "error",
            "error": "快麦商品档案无尺寸（x/y/z），请 C 在快麦商品档案维护或在 km_sku_map 导入",
            "attrs": attrs,
            "km_dims_missing": True,
        }
    ps = prebuilt_ps
    if not (ps and ps.get("dimensions_ok")):
        ps = pspec.build_production_spec(
            raw_attrs,
            max(qty, 1),
            title=title or "",
            material_mapping=mat_map,
        )
    if ps.get("dimensions_ok") and all(ps.get(k) is not None for k in ("length", "width", "height")):
        l, w, h = float(ps["length"]), float(ps["width"]), float(ps["height"])
        if not material_text and ps.get("material"):
            material_text = str(ps["material"])
    else:
        if (sku or "").strip():
            return {
                "status": "error",
                "error": "快麦商品档案无尺寸（x/y/z），请 C 在快麦商品档案维护",
                "attrs": attrs,
                "km_dims_missing": True,
            }
        dims = pspec.parse_dimensions_for_item(raw_attrs, title or "")
        if not pspec.dimensions_ready_for_calc(dims):
            missing = ps.get("dimensions_missing") or pspec.missing_dimension_labels(dims)
            if missing:
                err = f"规格缺少{'、'.join(missing)}，无法算料（需长宽高齐全，单位已统一为cm）"
            else:
                err = "无法从规格解析长宽高，无法算料"
            return {
                "status": "error",
                "error": err,
                "attrs": attrs,
                "dimensions_missing": missing,
            }
        l, w, h = float(dims["l"]), float(dims["w"]), float(dims["h"])
    pt = infer_product_type_for_calc(order_type, clean_attrs or attrs)
    is_buckle = pt in ("带扣", "daikou")
    calc_pt = (
        "纸箱"
        if pt == "纸箱"
        else "扣底盒"
        if pt == "扣底盒"
        else "双插盒"
        if pt == "双插盒"
        else "飞机盒"
    )

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

    paper = match_paper(
        paper_l_inch,
        paper_w_inch,
        material_text,
        raw_rows,
        product_type=pt,
        attrs=clean_attrs or attrs,
        shortage_label=calc_pt,
        box_l_cm=l,
        box_w_cm=w,
        box_h_cm=h,
    )
    if not paper.get("success"):
        st = "shortage" if paper.get("shortage") else "error"
        err = paper.get("error", "纸板匹配失败")
        return {
            "status": st,
            "material_status": st,
            "error": err,
            "shortage_detail": paper.get("shortage_detail") or err,
            "paper_l_inch": paper_l_inch,
            "paper_w_inch": paper_w_inch,
            "inches": inches,
            "material": material_text,
            "attrs": attrs,
            "nearest_paper": paper.get("nearest_paper"),
            "product_label": calc_pt,
            "box_l_cm": l,
            "box_w_cm": w,
            "box_h_cm": h,
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

    import dimoldb_store as ds
    import km_sku_resolve as ksr

    ps_for_dm = ps if isinstance(ps, dict) else {}
    if not ps_for_dm.get("platform_spec_raw"):
        ps_for_dm = {**ps_for_dm, "platform_spec_raw": raw_attrs}
    dm_index = ds.build_dim_match_index(dimoldb) if dimoldb else None
    dm_info = ksr.match_dimoldb_for_line(
        ps_for_dm,
        order_type,
        dimoldb,
        dm_index,
        sku=sku,
    )
    if dm_info.get("skip"):
        dm = {"success": False, "skip": True}
    elif dm_info.get("matched"):
        dm = {
            "success": True,
            "dimoldb_id": dm_info.get("dimoldb_id") or "",
            "code": dm_info.get("dimoldb_code") or "",
            "display_code": dm_info.get("dimoldb_code") or "",
            "name": "",
        }
    else:
        dm = match_dimoldb(
            l,
            w,
            h,
            dimoldb,
            pt,
            diameter_type=str((ps_for_dm or {}).get("diameter_type") or ""),
        )
    if dm.get("skip"):
        dimoldb_id = ""
        dimoldb_label = "无刀模"
    elif dm.get("success"):
        dimoldb_id = dm.get("dimoldb_id") or ""
        dimoldb_label = dimoldb_id or dm.get("code") or ""
    else:
        dimoldb_id = ""
        dimoldb_label = "未匹配"

    spec_label, carton_layer = _format_carton_paper_display(
        paper,
        mat_key=mat_key,
        material_text=material_text,
    )

    return {
        "status": "done",
        "material_status": "done",
        "attrs": attrs,
        "qty": qty,
        "material": material_text or mat_key,
        "material_key": mat_key,
        "carton_layer_label": carton_layer,
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
        "dimoldb_id": dimoldb_id,
        "dimoldb_code": (dm.get("code") or dm.get("display_code") or "")
        if dm.get("success")
        else "",
        "dimoldb_name": dm.get("name") if dm.get("success") else "",
        "dimoldb_label": dimoldb_label,
    }


def _format_carton_paper_display(
    paper: dict[str, Any],
    *,
    mat_key: str = "",
    material_text: str = "",
) -> tuple[str, str]:
    """算料纸板展示：层数放最前，员工一眼能区分 3层 / 5层。"""
    import production_spec as pspec

    name = str(paper.get("name") or "")
    blob = " ".join(x for x in (material_text, name, mat_key) if x)
    layer = pspec.infer_carton_layer_label(blob, material_text, mat_key)
    supplier = str(paper.get("supplier") or "").strip()
    spec = str(paper.get("paper_spec") or "").strip()
    if layer:
        head = f"【{layer}】"
    elif mat_key == "b_keng":
        head = "【3层纸箱】"
        layer = "3层纸箱"
    elif mat_key in ("eb_keng", "bc_keng"):
        head = "【5层纸箱】"
        layer = "5层纸箱"
    else:
        head = ""
    body = " ".join(x for x in (supplier, name, spec) if x)
    display = f"{head}{body}".strip() if head else body
    return display, layer


def mark_flow_calc_done(
    db_config: dict,
    processes: list,
    order: dict,
    order_type: str,
    internal_order_id_fn: Callable,
    get_or_create_flow_steps_fn: Callable,
    save_flow_row_fn: Callable,
) -> None:
    if not order:
        return
    oid = internal_order_id_fn(order)
    steps = get_or_create_flow_steps_fn(db_config, processes, oid, order_type)
    for s in steps:
        if (s.get("step") or s.get("name")) == "算料":
            s["done"] = True
            s["active"] = False
            break
    save_flow_row_fn(db_config, oid, order_type, steps)


def calc_order_line(
    order: dict,
    line_index: int,
    *,
    quote_data: dict,
    raw_rows: list[dict],
    dimoldb: list[dict],
    material_mapping: list[dict],
    mark_flow: bool = False,
    db_config: dict | None = None,
    processes: list | None = None,
    internal_order_id_fn: Callable | None = None,
    infer_order_type_fn: Callable | None = None,
    get_or_create_flow_steps_fn: Callable | None = None,
    save_flow_row_fn: Callable | None = None,
    km_index: dict | None = None,
    fetch_km_product: bool = False,
) -> dict[str, Any]:
    import production_spec as pspec

    items = order.get("items") or []
    if line_index < 0 or line_index >= len(items):
        return {"status": "error", "error": "子单行号无效"}
    it = items[line_index]
    import km_sku_map_store as kms
    import km_sku_resolve as ksr

    if km_index is None:
        km_index = kms.load_all()
    ctx = ksr.resolve_line_context(
        it,
        km_index=km_index,
        material_mapping=material_mapping,
        fetch_if_missing=fetch_km_product,
    )
    order_raw = ctx.get("order_spec_raw") or ctx["raw_attrs"]
    raw_attrs = order_raw
    try:
        import production_helpers as ph

        if not raw_attrs:
            raw_attrs = ph.item_buyer_attrs(it)
    except Exception:
        pass
    item_name = (it.get("name") or "").strip()
    attrs = pspec.sanitize_sku_attrs(raw_attrs) or raw_attrs
    order_qty = int(it.get("qty") or 0)
    ps = pspec.build_production_spec(
        raw_attrs,
        order_qty,
        title=item_name,
        material_mapping=material_mapping or [],
    )
    ps = ksr.enrich_production_spec(
        ps,
        ctx.get("km_row"),
        material_mapping=material_mapping,
        order_spec_raw=ctx.get("order_spec_raw") or raw_attrs,
        km_product=ctx.get("km_product"),
        sku=ctx.get("sku") or "",
    )
    qty = int(ps.get("qty") or order_qty)
    material_text = ps.get("material") or pspec.match_production_material(
        raw_attrs, material_mapping
    ) or ""
    type_blob = " ".join(
        x
        for x in (
            raw_attrs,
            material_text,
            (ctx.get("km_product") or {}).get("material_hint") or "",
            ps.get("line2") or "",
        )
        if x
    )
    order_type = infer_product_type_for_calc(
        infer_order_type_fn(order) if infer_order_type_fn else "",
        type_blob,
    )

    result = calc_material_line(
        attrs=raw_attrs or ps.get("line2") or ps.get("formatted") or "",
        qty=qty,
        order_type=order_type,
        material_text=material_text,
        quote_data=quote_data,
        raw_rows=raw_rows,
        dimoldb=dimoldb,
        title=item_name,
        prebuilt_ps=ps,
        sku=ctx.get("sku") or "",
    )
    so_id = str(order.get("so_id") or order.get("sid") or "")
    set_cached_line(so_id, line_index, result)

    if mark_flow and result.get("status") == "done" and db_config and internal_order_id_fn:
        mark_flow_calc_done(
            db_config,
            processes or [],
            order,
            order_type,
            internal_order_id_fn,
            get_or_create_flow_steps_fn,
            save_flow_row_fn,
        )
    return result


def auto_calc_all_orders(
    orders: list[dict],
    *,
    quote_data: dict,
    load_raw_fn: Callable[[], list[dict]],
    load_dimoldb_fn: Callable[[], list[dict]],
    material_mapping: list[dict],
    mark_flow: bool = False,
    db_config: dict | None = None,
    processes: list | None = None,
    internal_order_id_fn: Callable | None = None,
    infer_order_type_fn: Callable | None = None,
    get_or_create_flow_steps_fn: Callable | None = None,
    save_flow_row_fn: Callable | None = None,
    only_so_ids: set[str] | None = None,
) -> dict[str, Any]:
    """订单同步后批量算料，结果写入 material_calc_cache.json。"""
    import km_sku_map_store as kms

    raw_rows = load_raw_rows(load_raw_fn)
    dimoldb = load_dimoldb_fn()
    km_index = kms.load_all()
    done = failed = 0
    errors: list[str] = []

    for order in orders or []:
        so_id = str(order.get("so_id") or order.get("sid") or "")
        if only_so_ids is not None and so_id not in only_so_ids:
            continue
        for idx, _it in enumerate(order.get("items") or []):
            try:
                r = calc_order_line(
                    order,
                    idx,
                    quote_data=quote_data,
                    raw_rows=raw_rows,
                    dimoldb=dimoldb,
                    material_mapping=material_mapping,
                    mark_flow=mark_flow,
                    db_config=db_config,
                    processes=processes,
                    internal_order_id_fn=internal_order_id_fn,
                    infer_order_type_fn=infer_order_type_fn,
                    get_or_create_flow_steps_fn=get_or_create_flow_steps_fn,
                    save_flow_row_fn=save_flow_row_fn,
                    km_index=km_index,
                    fetch_km_product=False,
                )
                if r.get("status") in ("done", "shortage"):
                    done += 1
                else:
                    failed += 1
                    errors.append(f"{so_id}#{idx}: {r.get('error','')}")
            except Exception as ex:
                failed += 1
                errors.append(f"{so_id}#{idx}: {ex}")

    return {
        "success": True,
        "lines_done": done,
        "lines_failed": failed,
        "errors": errors[:50],
    }


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


def _normalize_cached_shortage(entry: dict | None) -> dict | None:
    """旧算料缓存可能仍是「最近纸板…」文案，读缓存时统一成新格式。"""
    if not entry or entry.get("status") != "shortage":
        return entry
    err = str(entry.get("error") or entry.get("shortage_detail") or "")
    if "展开需纸长" in err and "最近纸板" not in err:
        return entry
    pl = float(entry.get("paper_l_inch") or 0)
    pw = float(entry.get("paper_w_inch") or 0)
    if pl <= 0 or pw <= 0:
        return entry
    l = float(entry.get("box_l_cm") or 0)
    w = float(entry.get("box_w_cm") or 0)
    h = float(entry.get("box_h_cm") or 0)
    if l <= 0 or w <= 0 or h <= 0:
        import production_spec as pspec

        attrs = (entry.get("attrs") or "").strip()
        ps = pspec.build_production_spec(attrs, 1)
        if ps.get("dimensions_ok"):
            l = float(ps.get("length") or 0)
            w = float(ps.get("width") or 0)
            h = float(ps.get("height") or 0)
    if l <= 0 or w <= 0:
        return entry
    pt = (
        entry.get("product_label")
        or entry.get("product_type")
        or "产品"
    )
    msg = format_paper_shortage_message(
        product_label=str(pt),
        length_cm=l,
        width_cm=w,
        height_cm=h or 0,
        paper_l_inch=pl,
        paper_w_inch=pw,
    )
    out = dict(entry)
    out["error"] = msg
    out["shortage_detail"] = msg
    return out


def get_cached_line(so_id: str, line_index: int) -> dict | None:
    raw = load_calc_cache().get(cache_key(so_id, line_index))
    return _normalize_cached_shortage(raw)


def set_cached_line(so_id: str, line_index: int, result: dict) -> None:
    data = load_calc_cache()
    data[cache_key(so_id, line_index)] = {
        **result,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_calc_cache(data)
