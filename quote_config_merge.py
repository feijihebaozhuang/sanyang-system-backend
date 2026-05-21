# -*- coding: utf-8 -*-
"""报价配置合并：save_config 只 patch 用户修改字段，不全量覆盖。"""
from __future__ import annotations

import copy
from typing import Any


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
            base["material_mapping"] = [
                _normalize_material_row(row)
                for row in val
                if isinstance(row, dict)
            ]
        elif isinstance(val, dict) and isinstance(base.get(key), dict):
            sub = base[key]
            for sk, sv in val.items():
                if isinstance(sv, dict) and isinstance(sub.get(sk), dict):
                    for mk, mv in sv.items():
                        if isinstance(mv, dict) and isinstance(sub[sk].get(mk), dict):
                            sub[sk][mk].update(mv)
                        else:
                            sub[sk][mk] = mv
                else:
                    sub[sk] = sv
        else:
            base[key] = val
    return base
