# -*- coding: utf-8 -*-
"""报价配置合并：save_config 只 patch 用户修改字段，不全量覆盖。"""
from __future__ import annotations

import copy
from typing import Any

from quote_material_defaults import enrich_material_mapping


def _deep_merge(target: dict, patch: dict) -> dict:
    """只更新 patch 里出现的键，保留 target 其余字段（避免 price patch 清掉 name/gram_weight）。"""
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(target.get(k), dict):
            _deep_merge(target[k], v)
        else:
            target[k] = copy.deepcopy(v) if isinstance(v, dict) else v
    return target


def _normalize_material_row(row: dict) -> dict:
    name = (row.get("material_name") or row.get("label") or "").strip()
    key = (row.get("material_key") or name or "").strip()
    out = dict(row)
    out["material_name"] = name
    out["material_key"] = key
    if name:
        out.setdefault("label", name)
    return out


def merge_quote_config(existing: dict | None, patch: dict | None) -> dict:
    """合并报价配置：只更新 patch 中出现的字段，保留用户已有 material_mapping 等。"""
    base = copy.deepcopy(existing) if isinstance(existing, dict) else {}
    if not isinstance(patch, dict) or not patch:
        return base
    for key, val in patch.items():
        if key == "material_mapping" and isinstance(val, list):
            if not val:
                continue
            base["material_mapping"] = enrich_material_mapping(
                [
                    _normalize_material_row(row)
                    for row in val
                    if isinstance(row, dict)
                ]
            )
        elif isinstance(val, dict):
            if isinstance(base.get(key), dict):
                _deep_merge(base[key], val)
            else:
                base[key] = copy.deepcopy(val)
        else:
            base[key] = val
    return base
