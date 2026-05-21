# -*- coding: utf-8 -*-
"""报价配置合并：save_config 只 patch 用户修改字段，不全量覆盖。"""
from __future__ import annotations

import copy
from typing import Any


def merge_quote_config(existing: dict | None, patch: dict | None) -> dict:
    """合并报价配置：只更新 patch 中出现的字段，保留用户已有 material_mapping 等。"""
    base = copy.deepcopy(existing) if isinstance(existing, dict) else {}
    if not isinstance(patch, dict) or not patch:
        return base
    for key, val in patch.items():
        if key == "material_mapping" and isinstance(val, list):
            if not val:
                continue
            rows = list(base.get("material_mapping") or [])
            by_id: dict[str, dict[str, Any]] = {}
            for i, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                rid = str(row.get("material_key") or row.get("material_name") or i)
                by_id[rid] = row
            for row in val:
                if not isinstance(row, dict):
                    continue
                rid = str(row.get("material_key") or row.get("material_name") or "")
                if rid in by_id:
                    cur = by_id[rid]
                    if "keywords" in row:
                        cur["keywords"] = row["keywords"]
                    if row.get("group"):
                        cur["group"] = row["group"]
                else:
                    rows.append(row)
                    by_id[rid] = row
            base["material_mapping"] = rows
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
