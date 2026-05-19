#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
刀模库 dimoldb 重复/冲突/无 code 排查与清理。

用法（在项目根目录，已配置 .env）：
  python scripts/dimoldb_data_cleanup.py audit
  python scripts/dimoldb_data_cleanup.py delete-exact-dupes          # 仅预览
  python scripts/dimoldb_data_cleanup.py delete-exact-dupes --apply   # 删除纯重复
  python scripts/dimoldb_data_cleanup.py export-conflicts
  python scripts/dimoldb_data_cleanup.py export-no-code --limit 5000

输出目录默认：scripts/output/dimoldb_cleanup/
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pymysql

from settings import get_db_config

CONFLICT_CODES = ("1450", "6036", "8361")
OUTPUT_DIR = Path(__file__).resolve().parent / "output" / "dimoldb_cleanup"

SELECT_COLS = (
    "id",
    "product_type",
    "name",
    "code",
    "production_spec",
    "km_mapping_code",
    "length",
    "width",
    "height",
    "remark",
    "stock",
    "created_at",
)


def connect():
    cfg = get_db_config()
    return pymysql.connect(**cfg, cursorclass=pymysql.cursors.DictCursor)


def _norm_code(v) -> str:
    return str(v or "").strip()


def _dim_key(row: dict) -> tuple:
    """同 code + 同规格指纹（纯重复判定）。"""
    return (
        _norm_code(row.get("code")),
        (row.get("product_type") or "").strip(),
        round(float(row.get("length") or 0), 3),
        round(float(row.get("width") or 0), 3),
        round(float(row.get("height") or 0), 3),
        (row.get("name") or "").strip(),
        (row.get("remark") or "").strip(),
        (row.get("production_spec") or "").strip(),
    )


def _spec_label(row: dict) -> str:
    l, w, h = row.get("length"), row.get("width"), row.get("height")
    return f"{l}×{w}×{h}"


def fetch_all(cur) -> list[dict]:
    cols = ", ".join(f"`{c}`" for c in SELECT_COLS)
    cur.execute(f"SELECT {cols} FROM dimoldb ORDER BY id ASC")
    return list(cur.fetchall())


def cmd_audit(cur) -> None:
    rows = fetch_all(cur)
    total = len(rows)
    print(f"总记录数: {total}")

    with_code = [r for r in rows if _norm_code(r.get("code"))]
    no_code = [r for r in rows if not _norm_code(r.get("code"))]
    print(f"有 code: {len(with_code)}")
    print(f"无 code: {len(no_code)}")

    # 纯重复（有 code，同指纹多条）
    by_key: dict[tuple, list] = defaultdict(list)
    for r in with_code:
        by_key[_dim_key(r)].append(r)
    exact_groups = [g for g in by_key.values() if len(g) > 1]
    dup_rows = sum(len(g) - 1 for g in exact_groups)
    print(f"纯重复组数: {len(exact_groups)}，可删条数: {dup_rows}")
    for g in exact_groups[:20]:
        g_sorted = sorted(g, key=lambda x: x["id"])
        keep, drops = g_sorted[0], g_sorted[1:]
        print(
            f"  code={_norm_code(keep['code'])} spec={_spec_label(keep)} "
            f"keep id={keep['id']} drop ids={[d['id'] for d in drops]}"
        )

    # 同 code 多规格
    by_code: dict[str, list] = defaultdict(list)
    for r in with_code:
        by_code[_norm_code(r["code"])].append(r)
    multi_spec = []
    for code, items in by_code.items():
        specs = {_spec_label(x) for x in items}
        if len(specs) > 1:
            multi_spec.append((code, len(items), len(specs), sorted(specs)))
    multi_spec.sort(key=lambda x: -x[1])
    print(f"同 code 多规格（冲突）: {len(multi_spec)} 个 code")
    for code, cnt, sc, specs in multi_spec[:30]:
        mark = " ⚠️" if code in CONFLICT_CODES else ""
        print(f"  {code}: {cnt} 条, {sc} 种规格{mark} -> {specs[:5]}{'...' if len(specs)>5 else ''}")

    # 无 code 按类型
    nc_type: dict[str, int] = defaultdict(int)
    for r in no_code:
        nc_type[r.get("product_type") or "(空)"] += 1
    print("无 code 按 product_type:")
    for pt, n in sorted(nc_type.items(), key=lambda x: -x[1]):
        print(f"  {pt}: {n}")

    unique_codes = len(by_code)
    print(f"唯一 code 数: {unique_codes}")


def cmd_delete_exact_dupes(cur, apply: bool) -> None:
    rows = fetch_all(cur)
    by_key: dict[tuple, list] = defaultdict(list)
    for r in rows:
        c = _norm_code(r.get("code"))
        if not c:
            continue
        by_key[_dim_key(r)].append(r)

    to_delete: list[int] = []
    for g in by_key.values():
        if len(g) < 2:
            continue
        g_sorted = sorted(g, key=lambda x: x["id"])
        to_delete.extend(int(x["id"]) for x in g_sorted[1:])

    to_delete = sorted(set(to_delete))
    print(f"将删除 {len(to_delete)} 条纯重复: ids={to_delete}")
    if not to_delete:
        return
    if not apply:
        print("（预览模式，加 --apply 执行 DELETE）")
        return

    placeholders = ",".join(["%s"] * len(to_delete))
    cur.execute(f"DELETE FROM dimoldb WHERE id IN ({placeholders})", to_delete)
    print(f"已删除 {cur.rowcount} 条")


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            out = {}
            for k, v in r.items():
                if isinstance(v, Decimal):
                    out[k] = float(v)
                else:
                    out[k] = v
            w.writerow(out)
    print(f"已写入 {path} ({len(rows)} 行)")


def cmd_export_conflicts(cur) -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    codes = CONFLICT_CODES
    placeholders = ",".join(["%s"] * len(codes))
    cols = ", ".join(f"`{c}`" for c in SELECT_COLS)
    cur.execute(
        f"SELECT {cols} FROM dimoldb WHERE TRIM(code) IN ({placeholders}) ORDER BY code, length, width, height, id",
        codes,
    )
    rows = cur.fetchall()
    _write_csv(OUTPUT_DIR / f"conflict_codes_{ts}.csv", rows)

    # 同 code 多规格全量（供人工扫）
    cur.execute(
        f"""
        SELECT code, COUNT(*) AS cnt,
               COUNT(DISTINCT CONCAT(ROUND(length,3),'x',ROUND(width,3),'x',ROUND(height,3))) AS spec_cnt
        FROM dimoldb
        WHERE TRIM(code) != ''
        GROUP BY TRIM(code)
        HAVING spec_cnt > 1
        ORDER BY cnt DESC
        """
    )
    summary = cur.fetchall()
    _write_csv(OUTPUT_DIR / f"all_multi_spec_codes_{ts}.csv", summary)


def cmd_export_no_code(cur, limit: int) -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    cols = ", ".join(f"`{c}`" for c in SELECT_COLS)

    cur.execute(
        """
        SELECT product_type, COUNT(*) AS cnt
        FROM dimoldb
        WHERE TRIM(IFNULL(code,'')) = ''
        GROUP BY product_type
        ORDER BY cnt DESC
        """
    )
    _write_csv(OUTPUT_DIR / f"no_code_by_type_{ts}.csv", cur.fetchall())

    cur.execute(
        f"""
        SELECT {cols} FROM dimoldb
        WHERE TRIM(IFNULL(code,'')) = ''
        ORDER BY product_type, remark, id
        LIMIT %s
        """,
        (limit,),
    )
    _write_csv(OUTPUT_DIR / f"no_code_sample_{ts}.csv", cur.fetchall())

    cur.execute(
        """
        SELECT product_type,
               CASE WHEN TRIM(IFNULL(remark,'')) != '' THEN 'has_remark' ELSE 'no_remark' END AS remark_flag,
               COUNT(*) AS cnt
        FROM dimoldb
        WHERE TRIM(IFNULL(code,'')) = ''
        GROUP BY product_type, remark_flag
        ORDER BY cnt DESC
        """
    )
    _write_csv(OUTPUT_DIR / f"no_code_remark_summary_{ts}.csv", cur.fetchall())


def main() -> int:
    parser = argparse.ArgumentParser(description="刀模库数据清理工具")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("audit", help="统计重复/冲突/无 code")
    p_del = sub.add_parser("delete-exact-dupes", help="删除同 code+同规格纯重复（保留最小 id）")
    p_del.add_argument("--apply", action="store_true", help="真正执行 DELETE")
    sub.add_parser("export-conflicts", help="导出冲突 code 与全部多规格 code 列表")
    p_nc = sub.add_parser("export-no-code", help="导出无 code 汇总与样本")
    p_nc.add_argument("--limit", type=int, default=5000, help="样本行数上限")

    args = parser.parse_args()
    db = connect()
    try:
        cur = db.cursor()
        if args.cmd == "audit":
            cmd_audit(cur)
        elif args.cmd == "delete-exact-dupes":
            cmd_delete_exact_dupes(cur, args.apply)
            if args.apply:
                db.commit()
        elif args.cmd == "export-conflicts":
            cmd_export_conflicts(cur)
        elif args.cmd == "export-no-code":
            cmd_export_no_code(cur, args.limit)
        else:
            parser.error("unknown command")
            return 2
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
