# -*- coding: utf-8 -*-
"""报价 material_mapping 默认 keywords（空字段自动补全，避免纸箱类无法匹配）。"""
from __future__ import annotations

from typing import Any

# material_key → 默认 keywords（英文逗号分隔）
MATERIAL_KEYWORD_DEFAULTS: dict[str, str] = {
    "d6d": "特硬,D6D,国产,材质,加硬",
    "taiwan": "台湾,进口,超硬",
    "w7w": "白色,W7W,双白",
    "black": "黑色,黑卡",
    "red": "红色",
    "q7q": "优质,Q7Q,特价,优惠,差材料",
    "p6d": "P6D",
    "b_keng": "B坑,B瓦,三层,3层,K7K,普通",
    "eb_keng": "五层,EB,EB坑,五层EB,K636K",
    "bc_keng": "五层,BC,BC坑,五层BC,K737K",
}


def _merge_keyword_csv(existing: str, default: str) -> str:
    ex = (existing or "").strip()
    if not ex:
        return default
    if not default:
        return ex
    seen = {k.strip().lower() for k in ex.split(",") if k.strip()}
    add: list[str] = []
    for k in default.split(","):
        k = k.strip()
        if k and k.lower() not in seen:
            seen.add(k.lower())
            add.append(k)
    return ex if not add else ex + "," + ",".join(add)


def enrich_material_mapping(
    rows: list[dict] | None, *, merge_defaults: bool = True
) -> list[dict]:
    """补全空 keywords；merge_defaults=False 时仅填空、不追加默认词（admin 保存用）。"""
    if not isinstance(rows, list):
        return []
    out: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        r = dict(row)
        key = (r.get("material_key") or "").strip()
        default = MATERIAL_KEYWORD_DEFAULTS.get(key, "")
        if default:
            cur = str(r.get("keywords") or "").strip()
            if not cur:
                r["keywords"] = default
            elif merge_defaults:
                r["keywords"] = _merge_keyword_csv(cur, default)
        name = (r.get("material_name") or r.get("label") or "").strip()
        if name:
            r.setdefault("material_name", name)
            r.setdefault("label", name)
        if key:
            r.setdefault("material_key", key)
        out.append(r)
    return out


def enrich_quote_data(qd: dict | None, *, merge_defaults: bool = True) -> dict:
    """对整份报价配置补全 material_mapping keywords。"""
    if not isinstance(qd, dict):
        return {}
    base = dict(qd)
    base["material_mapping"] = enrich_material_mapping(
        base.get("material_mapping") or [], merge_defaults=merge_defaults
    )
    return base
