#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将 dimoldb_merged.json 覆盖写入 MySQL（在 213 stable 目录执行）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import dimoldb_store as ds
from settings import DB_CONFIG
import pymysql


def get_db():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)


def main() -> None:
    path = ROOT / "data" / "import" / "dimoldb" / "dimoldb_merged.json"
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    items = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        raise SystemExit("JSON 应为数组")
    if not ds.save_dimoldb(get_db, items):
        raise SystemExit("save_dimoldb 失败")
    ds.invalidate_dimoldb_cache()
    print(f"已写入 {len(items)} 条 → dimoldb 表")


if __name__ == "__main__":
    main()
