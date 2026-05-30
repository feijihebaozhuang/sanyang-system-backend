# -*- coding: utf-8 -*-
"""
3001/3002 权限策略：已废弃细粒度权限矩阵。
登录即可使用全部业务功能；员工/权限配置仅在 3003（guanli）管理。
"""
from __future__ import annotations

PERM_FEATURES = [
    "首页",
    "订单生产进度",
    "扫码报工",
    "日报表",
    "数据看板",
    "刀模",
    "刀模库",
    "库存",
    "原材料",
    "快麦ERP",
    "员工",
    "权限管理",
    "报价",
    "实时订单",
]

GUANLI_ADMIN_URL = "https://feijihe.top/guanli/"


def all_features_true() -> dict[str, bool]:
    return {f: True for f in PERM_FEATURES}


def user_has_any_feature(user: dict | None) -> bool:
    return bool(user)


def user_has_feature(user: dict | None, _username: str, _feature: str) -> bool:
    return bool(user)


def my_permissions_response(
    user: dict | None,
    *,
    all_employees: list | None = None,
) -> dict:
    perms = all_features_true()
    return {
        "success": True,
        "my_permissions": perms,
        "all_permissions": {},
        "permissions_overrides": {},
        "role_permissions": {},
        "employee_roles": {},
        "all_employees": all_employees or [],
        "permissions_mode": "open",
        "guanli_admin_url": GUANLI_ADMIN_URL,
    }
