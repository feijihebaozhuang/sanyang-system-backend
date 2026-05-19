# -*- coding: utf-8 -*-
"""
系统硬编码配置（唯一来源）。
部署只覆盖 .py；材料映射、默认工序、刀模匹配容差等均由此模块提供，不读 JSON 配置。
"""
from __future__ import annotations

import copy
from typing import Any

# ----- 纸箱材质关键词 → 生产标签（正则/子串匹配，长关键词优先） -----
CARTON_MATERIAL_RULES: list[tuple[str, str]] = [
    ("特硬,外径特硬,内径特硬,D6D,国产,加硬", "特硬"),
    ("优质,Q7Q,特价", "优质"),
    ("台湾,进口,超硬", "台湾"),
    ("白色,W7W,双白", "白色"),
    ("黑色,黑卡", "黑色"),
    ("红色", "红色"),
    ("P6D", "P6D"),
    ("B坑,K7K,三层", "B坑"),
    ("EB坑,K636K,五层EB", "EB坑"),
    ("BC坑,K737K,五层BC", "BC坑"),
    ("E瓦,瓦楞", "E瓦"),
]

# ----- 默认生产线工序（树形，与权限页一致） -----
DEFAULT_PROCESSES: list[dict[str, Any]] = [
    {
        "dept": "美丽湾工厂部",
        "steps": [
            {"id": 1, "name": "客服接单"},
            {"id": 2, "name": "黄厂打印"},
            {"id": 3, "name": "审单分单"},
            {"id": 4, "name": "算料"},
            {"id": 5, "name": "分纸"},
            {"id": 6, "name": "啤机(自动平压平)"},
            {"id": 7, "name": "啤机(机械手)"},
            {"id": 8, "name": "手啤"},
            {"id": 9, "name": "印刷"},
            {"id": 10, "name": "清废"},
            {"id": 11, "name": "打包发货"},
        ],
    },
    {
        "dept": "纸箱部",
        "steps": [
            {"id": 1, "name": "客服接单"},
            {"id": 2, "name": "黄厂打印"},
            {"id": 3, "name": "审单分单"},
            {"id": 4, "name": "算料"},
            {"id": 5, "name": "分纸"},
            {"id": 6, "name": "印刷"},
            {"id": 7, "name": "开槽/打角"},
            {"id": 8, "name": "粘胶/打钉"},
            {"id": 9, "name": "打包发货"},
        ],
    },
]

DEFAULT_POSITIONS: list[str] = [
    "超级管理员",
    "主管",
    "客服",
    "员工",
    "财务",
    "业务员",
]

# 默认员工（权限字段由 _sync_all_employees_perms 补齐）
DEFAULT_EMPLOYEES: list[dict[str, str]] = [
    {"name": "戴雅利", "position": "超级管理员"},
    {"name": "邓涛", "position": "主管"},
    {"name": "黄兴", "position": "主管"},
    {"name": "覃海霞", "position": "主管"},
    {"name": "蒋义红", "position": "主管"},
    {"name": "沈齐豪", "position": "主管"},
    {"name": "苏世婷", "position": "客服"},
    {"name": "廖思美", "position": "客服"},
    {"name": "张慧平", "position": "客服"},
    {"name": "陈贝贝", "position": "客服"},
    {"name": "罗怡", "position": "客服"},
    {"name": "周井梅", "position": "客服"},
    {"name": "戴志美", "position": "客服"},
    {"name": "石梅清", "position": "客服"},
    {"name": "张文杰", "position": "客服"},
    {"name": "何水单", "position": "业务员"},
    {"name": "李四军", "position": "员工"},
    {"name": "陈贤聪", "position": "业务员"},
    {"name": "姚斌", "position": "员工"},
    {"name": "隆浪", "position": "财务"},
]

# 刀模尺寸匹配容差（厘米）
DIMOLD_MATCH_TOLERANCE_CM: float = 0.6

# permission_data 中由本模块强制覆盖、不采纳 data.json 的键
HARDCODED_PERMISSION_KEYS: frozenset[str] = frozenset(
    {"processes", "production_material_mapping", "positions", "employees"}
)


def carton_material_mapping_rows() -> list[dict[str, str]]:
    """兼容旧 API 的 {keywords, label} 列表。"""
    return [
        {"keywords": kws, "label": label} for kws, label in CARTON_MATERIAL_RULES
    ]


def match_carton_material(text: str) -> str:
    """纸箱材质：按硬编码规则匹配关键词。"""
    low = (text or "").lower()
    best = ""
    best_len = 0
    for kws, label in CARTON_MATERIAL_RULES:
        for kw in (k.strip() for k in kws.split(",") if k.strip()):
            kl = kw.lower()
            if kl and kl in low and len(kw) > best_len:
                best = label
                best_len = len(kw)
    return best


def apply_hardcoded_permission_data(permission_data: dict) -> None:
    """将工序/材料映射/岗位/员工名单写回 permission_data（覆盖 JSON 中的同名字段）。"""
    permission_data["processes"] = copy.deepcopy(DEFAULT_PROCESSES)
    permission_data["production_material_mapping"] = carton_material_mapping_rows()
    permission_data["positions"] = list(DEFAULT_POSITIONS)
    permission_data["employees"] = copy.deepcopy(DEFAULT_EMPLOYEES)
