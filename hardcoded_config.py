# -*- coding: utf-8 -*-
"""
技术常量（非 admin 业务配置）。
业务配置（工序、材料映射、员工等）见 data.json —— 见 config_json.py。
"""
from __future__ import annotations

from typing import Any

# 刀模尺寸匹配容差（厘米，算法参数）
DIMOLD_MATCH_TOLERANCE_CM: float = 0.6

# 已废弃：勿再调用。保留空函数避免旧 import 报错。
HARDCODED_PERMISSION_KEYS: frozenset[str] = frozenset()


def apply_hardcoded_permission_data(permission_data: dict) -> None:
    """已废弃：配置以 data.json 为准，部署不覆盖 JSON。"""
    del permission_data


def carton_material_mapping_rows() -> list[dict[str, str]]:
    """已废弃：请读 permission_data.production_material_mapping。"""
    return []


def match_carton_material(text: str) -> str:
    """已废弃：请使用 config_json.match_material_from_mapping。"""
    return ""
