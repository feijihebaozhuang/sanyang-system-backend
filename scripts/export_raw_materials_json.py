#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MySQL raw_materials → data/import/raw_materials/raw_materials.json（小马哥 87 执行）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "import" / "raw_materials" / "raw_materials.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass


def main() -> int:
    import pymysql
    from settings import get_db_config

    cfg = dict(get_db_config())
    cfg.pop("autocommit", None)
    db = pymysql.connect(**cfg, autocommit=True, cursorclass=pymysql.cursors.DictCursor)
    cur = db.cursor()
    cur.execute(
        "SELECT supplier, name, paper_width, paper_length, qty "
        "FROM raw_materials ORDER BY id"
    )
    rows = cur.fetchall() or []
    cur.close()
    db.close()

    payload = [
        {
            "supplier": (r.get("supplier") or "").strip(),
            "name": (r.get("name") or "").strip(),
            "paper_width": str(r.get("paper_width") or "").strip(),
            "paper_length": str(r.get("paper_length") or "").strip(),
            "qty": int(r.get("qty") or 0),
        }
        for r in rows
    ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写入 {OUT} | {len(payload)} 条")
    print("提交: git add data/import/raw_materials/raw_materials.json && git commit -m '...' && git push")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
