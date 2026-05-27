#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在服务器上重置 3003 co_admin_user 的 admin 密码（勿提交密码到聊天）。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import customer_order_store as co


def main() -> int:
    p = argparse.ArgumentParser(description="重置 3003 admin 登录")
    p.add_argument("--username", default="admin")
    p.add_argument("--password", default="admin888", help="新密码明文")
    p.add_argument("--display-name", default="戴雅利")
    args = p.parse_args()
    co.ensure_tables()
    row = co._upsert_co_admin(
        args.username,
        co.password_hash(args.password),
        display_name=args.display_name,
        role="admin",
    )
    print(
        f"OK: username={row.get('username')} enabled={row.get('enabled')} "
        f"role={row.get('role')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
