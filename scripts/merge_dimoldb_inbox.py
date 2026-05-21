#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并 data/import/dimoldb 下 8 个标准文件 → dimoldb_merged.json（供 213 导入）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.import_dimoldb_auto import merge_items, merge_key, parse_workbook  # noqa: E402

INBOX = ROOT / "data" / "import" / "dimoldb"
ORDER = [
    "全量刀模_第1批(7列).xlsx",
    "全量刀模_第2批(7列).xlsx",
    "全量刀模_第3批(7列).xlsx",
    "全量刀模_第4批(7列).xlsx",
    "全量刀模v2_第1批9列.xlsx",
    "全量刀模v2_第2批9列.xlsx",
    "全量刀模v2_第3批9列.xlsx",
    "全量刀模v2_第4批9列.xlsx",
]


def main() -> None:
    reports = []
    for name in ORDER:
        p = INBOX / name
        if not p.is_file():
            raise SystemExit(f"缺少文件: {name}")
        reports.append(parse_workbook(p))
    items = merge_items(reports, prefer="larger")
    out = INBOX / "dimoldb_merged.json"
    out.write_text(json.dumps(items, ensure_ascii=False, indent=0), encoding="utf-8")
    no_code = sum(1 for it in items if not (it.get("code") or "").strip())
    dup_within = sum(reports[i]["rows"] for i in range(8)) - len(items)
    summary = {
        "merged_total": len(items),
        "no_code": no_code,
        "duplicate_rows_collapsed": dup_within,
        "source_rows_sum": sum(r["rows"] for r in reports),
        "strategy": "7列1-4批打底，v2九列1-4批覆盖同编码",
        "output": str(out),
    }
    (INBOX / "merge_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
