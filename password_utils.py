# -*- coding: utf-8 -*-
"""
密码工具：加盐 SHA256 哈希，向后兼容老的无盐哈希。

设计：
- 全局盐值来自环境变量 PASSWORD_SALT，未设置时用 FLASK_SECRET_KEY 兜底
- 哈希算法：SHA256(password_salt + plain_password)
- 验证时先验加盐哈希，再验老的无盐哈希（兼容迁移）
"""
from __future__ import annotations

import hashlib
import os


def _get_salt() -> str:
    """获取全局密码盐值。"""
    salt = os.getenv("PASSWORD_SALT", "").strip()
    if salt:
        return salt
    # FLASK_SECRET_KEY 兜底（所有 app 都有这个配置）
    from settings import FLASK_SECRET_KEY as _key
    return _key if _key else "sanyang_legacy_salt"


def hash_password(plain: str) -> str:
    """生成加盐密码哈希。"""
    raw = _get_salt() + (plain or "")
    return hashlib.sha256(raw.encode()).hexdigest()


def verify_password(plain: str, stored_hash: str) -> bool:
    """
    验证密码。优先验加盐哈希，失败后回退到无盐旧哈希。
    返回 True 表示匹配。
    """
    if not plain or not stored_hash:
        return False
    # 1. 试加盐哈希
    if hash_password(plain) == stored_hash:
        return True
    # 2. 试无盐旧哈希（兼容迁移期）
    legacy = hashlib.sha256((plain or "").encode()).hexdigest()
    if legacy == stored_hash:
        return True
    return False


def needs_rehash(stored_hash: str) -> bool:
    """
    判断是否需要重哈希（当前存储的是无盐旧哈希）。
    在上层发现 verify_password 返回 True 且 needs_rehash 返回 True 时，
    应调用 hash_password 更新存储的密码。
    """
    if not stored_hash:
        return False
    expected = hash_password("")
    if stored_hash == expected:
        return False
    # 尝试用无盐方式反向推断
    return True


def make_default_user_hash(username: str) -> str:
    """
    生成默认用户的加盐密码哈希。
    硬编码默认密码，供 USERS 字典初始化使用（迁移场景）。
    返回加盐哈希。
    """
    defaults = {
        "admin": "admin888",
        "daiyali": "admin888",
        "manager": "manager666",
        "worker": "worker123",
        "sushiting": "sushiting123",
        "liaosimei": "liaosimei123",
    }
    plain = defaults.get(username)
    if not plain:
        raise ValueError(f"未知默认用户: {username}")
    return hash_password(plain)
