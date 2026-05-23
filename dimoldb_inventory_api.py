# -*- coding: utf-8 -*-
"""刀模库 + 成品库存 API 共用逻辑（3001 客服 / 3002 生产 必须同一份）。"""
from __future__ import annotations

import re
from typing import Any, Callable

import dimoldb_store as ds

InferFn = Callable[[dict], str]

_MATERIAL_MAP = {
    "国产纸": "特硬D6D",
    "双白": "白色W7W",
    "台湾纸": "台湾纸",
    "黑色": "黑色",
    "红色": "红色",
    "差材料": "差材料",
}
_NAME_MAT_REPL = (("国产纸", "特硬D6D"), ("双白", "白色W7W"))
_TYPE_TO_INV = {
    "juxing": "changfang",
    "daikou": "changfang",
    "koudi": "changfang",
    "shuangcha": "changfang",
    "qita": "changfang",
    "changfang": "changfang",
    "zhengsquare": "zhengsquare",
}


def map_material(name: str) -> str:
    s = (name or "").strip()
    return _MATERIAL_MAP.get(s, s) if s else ""


def apply_inventory_material_labels(items: list[dict]) -> None:
    """库存列表：材质显示名 + name 内材质词替换（原地修改）。"""
    for item in items:
        if item.get("material"):
            item["material"] = map_material(item["material"])
        n = item.get("name", "")
        for old, new in _NAME_MAT_REPL:
            if old in n:
                item["name"] = n.replace(old, new)
                n = item["name"]


def filter_dimoldb_rows(
    rows: list[dict],
    *,
    ptype: str,
    search: str,
    dim_type: str,
    infer_fn: InferFn,
) -> list[dict]:
    data = list(rows)
    if ptype:
        if ptype == "zhengsquare-outer":
            data = [
                d
                for d in data
                if d.get("product_type") == "zhengsquare"
                and infer_fn(d) == "outer"
            ]
        elif ptype == "zhengsquare-inner":
            data = [
                d
                for d in data
                if d.get("product_type") == "zhengsquare"
                and infer_fn(d) == "inner"
            ]
        else:
            data = [d for d in data if d.get("product_type") == ptype]
    if dim_type and not ptype.startswith("zhengsquare-"):
        data = [d for d in data if infer_fn(d) == dim_type]
    if search:
        nums = re.findall(r"\d+\.?\d*", search.replace(" ", "*"))
        nums = [n for n in nums if n.strip()]
        if len(nums) >= 3:
            try:
                sl, sw, sh = float(nums[0]), float(nums[1]), float(nums[2])
                data = [
                    d
                    for d in data
                    if d.get("length") is not None
                    and abs(d["length"] - sl) < 0.1
                    and d.get("width") is not None
                    and abs(d["width"] - sw) < 0.1
                    and d.get("height") is not None
                    and abs(d["height"] - sh) < 0.1
                ]
            except (TypeError, ValueError):
                pass
        else:
            data = [
                d
                for d in data
                if search in d.get("name", "")
                or search in str(d.get("code") or "")
                or search in str(d.get("production_spec") or "")
                or search in str(d.get("km_mapping_code") or "")
                or f"{d.get('length', 0)}x{d.get('width', 0)}x{d.get('height', 0)}"
                in search
                or f"{d.get('length', 0)}×{d.get('width', 0)}×{d.get('height', 0)}"
                in search
            ]
    return data


def paginate_rows(
    rows: list[dict], page: int, page_size: int
) -> tuple[list[dict], int, int, int, int]:
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 50
    if page_size > 200:
        page_size = 200
    total = len(rows)
    total_pages = max(1, (total + page_size - 1) // page_size)
    start = (page - 1) * page_size
    end = start + page_size
    page_data = rows[start:end] if start < total else []
    return page_data, total, page, page_size, total_pages


def enrich_dimoldb_page(page_data: list[dict], inv_items: list[dict]) -> None:
    for d in page_data:
        d["stock"] = ds.calc_dimoldb_stock(d, inv_items)
        d["type_class"] = ds.infer_type_class(d)


def search_dimoldb_matches(
    db: list[dict], payload: dict[str, Any], infer_fn: InferFn
) -> list[dict]:
    ptype = payload.get("type", "")
    length = payload.get("length")
    width = payload.get("width")
    height = payload.get("height")
    dim_type = payload.get("dim_type", "")
    if (
        not ptype
        and length is None
        and width is None
        and height is None
        and not dim_type
    ):
        return []
    matches = list(db)
    if ptype:
        actual_type = ptype.replace("-outer", "").replace("-inner", "")
        matches = [d for d in matches if d.get("product_type") == actual_type]
        if "outer" in ptype and not payload.get("dim_type"):
            dim_type = "outer"
        elif "inner" in ptype and not payload.get("dim_type"):
            dim_type = "inner"
    if length is not None:
        lv = float(length)
        matches = [
            d for d in matches if abs(float(d.get("length", 0)) - lv) < 0.1
        ]
    if width is not None:
        wv = float(width)
        matches = [
            d for d in matches if abs(float(d.get("width", 0)) - wv) < 0.1
        ]
    if height is not None:
        hv = float(height)
        matches = [
            d for d in matches if abs(float(d.get("height", 0)) - hv) < 0.1
        ]
    ptype_for_dim = payload.get("type", "")
    if dim_type and ptype_for_dim == "zhengsquare":
        if dim_type == "inner":
            matches = [d for d in matches if infer_fn(d) == "inner"]
        elif dim_type == "outer":
            matches = [d for d in matches if infer_fn(d) == "outer"]
    elif dim_type and ptype_for_dim not in ("zhengsquare", "", None):
        has_inner_outer = any(infer_fn(d) for d in matches)
        if has_inner_outer and dim_type:
            if dim_type == "inner":
                matches = [d for d in matches if infer_fn(d) == "inner"]
            elif dim_type == "outer":
                matches = [d for d in matches if infer_fn(d) == "outer"]
    for d in matches:
        d["type_class"] = ds.infer_type_class(d)
        if not d.get("dim_type"):
            d["dim_type"] = infer_fn(d)
    return matches[:100]


def filter_inventory_rows(
    items: list[dict],
    *,
    ptype: str,
    search: str,
    length: str,
    width: str,
    height: str,
    search_field: str = "all",
) -> list[dict]:
    out = list(items)
    if ptype == "zhengsquare-outer":
        out = [
            d
            for d in out
            if d.get("product_type") == "zhengsquare" and d.get("dim_type") == "outer"
        ]
    elif ptype == "zhengsquare-inner":
        out = [
            d
            for d in out
            if d.get("product_type") == "zhengsquare" and d.get("dim_type") == "inner"
        ]
    elif ptype == "changfang-outer":
        out = [
            d
            for d in out
            if d.get("product_type") == "changfang" and d.get("dim_type") == "outer"
        ]
    elif ptype == "changfang-inner":
        out = [
            d
            for d in out
            if d.get("product_type") == "changfang" and d.get("dim_type") == "inner"
        ]
    elif ptype:
        inv_type = _TYPE_TO_INV.get(ptype, ptype)
        out = [d for d in out if d.get("product_type") == inv_type]
    if search:
        nums = re.findall(r"\d+\.?\d*", search.replace(" ", "*"))
        nums = [n for n in nums if n.strip()]
        if len(nums) >= 3:
            try:
                sl, sw, sh = float(nums[0]), float(nums[1]), float(nums[2])
                out = [
                    d
                    for d in out
                    if d.get("length") is not None
                    and abs(d["length"] - sl) < 0.1
                    and d.get("width") is not None
                    and abs(d["width"] - sw) < 0.1
                    and d.get("height") is not None
                    and abs(d["height"] - sh) < 0.1
                ]
            except (TypeError, ValueError):
                pass
        elif search.replace(".", "").replace("-", "").isdigit() or search.strip().replace(
            ".", ""
        ).replace("-", "").replace(",", "").replace("|", "").lstrip("-").isdigit():
            sv = float(search.strip().lstrip("-").replace(",", "."))
            out = [
                d
                for d in out
                if (d.get("length") is not None and abs(d["length"] - sv) < 0.1)
                or (d.get("width") is not None and abs(d["width"] - sv) < 0.1)
                or (d.get("height") is not None and abs(d["height"] - sv) < 0.1)
            ]
        elif search_field == "name":
            out = [d for d in out if search in d.get("name", "")]
        elif search_field == "material":
            out = [d for d in out if search in d.get("material", "")]
        else:
            out = [
                d
                for d in out
                if search in d.get("name", "") or search in d.get("material", "")
            ]
    if length:
        lv = float(length)
        out = [
            d
            for d in out
            if d.get("length") is not None and abs(float(d["length"]) - lv) < 0.1
        ]
    if width:
        wv = float(width)
        out = [
            d
            for d in out
            if d.get("width") is not None and abs(float(d["width"]) - wv) < 0.1
        ]
    if height:
        hv = float(height)
        out = [
            d
            for d in out
            if d.get("height") is not None and abs(float(d["height"]) - hv) < 0.1
        ]
    return out


def sort_inventory_rows(items: list[dict]) -> None:
    def sort_key(item: dict) -> tuple:
        try:
            dims = (
                item.get("name", "")
                .replace("×", "*")
                .replace("x", "*")
                .replace("X", "*")
                .split("*")
            )
            return (float(dims[0]), float(dims[1]), float(dims[2]))
        except (TypeError, ValueError, IndexError):
            return (9999, 9999, 9999)

    items.sort(key=sort_key)


def enrich_inventory_page(
    page_data: list[dict],
    dm_index: dict[tuple[str, float, float, float], list[dict]],
    infer_fn: InferFn,
) -> None:
    for item in page_data:
        if "stock" not in item and "qty" in item:
            item["stock"] = item["qty"]
        if item.get("dim_type") == "inner" and not item["name"].startswith("内径"):
            item["name"] = "内径" + item["name"]
        elif item.get("dim_type") == "outer" and not item["name"].startswith(
            "外径"
        ) and not item["name"].startswith("内"):
            item["name"] = "外径" + item["name"]
        item["dimoldb_info"] = ds.match_dimoldb_for_inventory_item(
            item, dm_index, infer_fn=infer_fn
        )
