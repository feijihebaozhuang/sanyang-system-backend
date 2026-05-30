# -*- coding: utf-8 -*-
"""
3001/3002 权限策略：按角色过滤功能权限。
员工只能使用扫码报工、日报表、员工出勤等基础功能；
管理/主管/超级管理员可使用全部功能。
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

# 员工默认可见功能（扫码报工、日报表、员工出勤、我的报工记录）
WORKER_FEATURES = {
    "首页": False,
    "订单生产进度": False,
    "扫码报工": True,
    "日报表": True,
    "数据看板": False,
    "刀模": False,
    "刀模库": False,
    "库存": False,
    "原材料": False,
    "快麦ERP": False,
    "员工": True,        # 员工出勤页
    "权限管理": False,
    "报价": False,
    "实时订单": False,
}

# 管理/主管可见全部功能
MANAGER_FEATURES = {f: True for f in PERM_FEATURES}
MANAGER_FEATURES["权限管理"] = False  # 权限管理仅超级管理员


def _infer_role_from_user(user: dict | None) -> str:
    if not user:
        return "员工"
    role = (user.get("role") or "").strip()
    if role in ("超级管理员", "管理", "主管", "管理员"):
        return role
    return "员工"


def user_has_any_feature(user: dict | None) -> bool:
    return bool(user)


def user_has_feature(user: dict | None, _username: str, feature: str) -> bool:
    """按角色判断是否有某个功能权限"""
    if not user:
        return False
    role = _infer_role_from_user(user)
    if role == "超级管理员":
        return True
    if role in ("管理", "主管", "管理员"):
        return MANAGER_FEATURES.get(feature, False)
    return WORKER_FEATURES.get(feature, False)


def my_permissions_response(
    user: dict | None,
    *,
    all_employees: list | None = None,
) -> dict:
    role = _infer_role_from_user(user)
    if role == "超级管理员":
        perms = {f: True for f in PERM_FEATURES}
    elif role in ("管理", "主管", "管理员"):
        perms = dict(MANAGER_FEATURES)
    else:
        perms = dict(WORKER_FEATURES)
    return {
        "success": True,
        "my_permissions": perms,
        "all_permissions": {},
        "permissions_overrides": {},
        "role_permissions": {},
        "employee_roles": {},
        "all_employees": all_employees or [],
        "permissions_mode": "role_based",
        "guanli_admin_url": GUANLI_ADMIN_URL,
    }
