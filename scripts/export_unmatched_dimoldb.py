#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成品飞机盒库存 vs 刀模库：导出「有成品规格、无刀模」列表。
输出格式与服务器 export_unmatched_dimoldb.txt 一致，便于 import_km_sku_map --txt-unmatched。
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import dimoldb_store as ds
import km_sku_map_store as kms


def _get_db():
    import pymysql
    from settings import get_db_config

    cfg = get_db_config()
    return pymysql.connect(**cfg, cursorclass=pymysql.cursors.DictCursor)


def load_inventory_finished() -> list[dict]:
    db = _get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT product_type, name, spec, length, width, height, qty, material, dim_type "
        "FROM inventory WHERE product_type IN ('zhengsquare','changfang','juxing') "
        "OR name LIKE '%飞机盒%' OR product_type LIKE '%square%'"
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    db.close()
    return rows


def load_dimoldb() -> list[dict]:
    return ds.load_dimoldb(_get_db, force=True)


def _spec_key(item: dict) -> tuple:
    l, w, h = ds._inventory_item_dims(item)
    pt = (item.get("product_type") or "").strip()
    if pt == "changfang":
        pt = "juxing"
    mat = (item.get("material") or item.get("spec") or item.get("name") or "").strip()
    return (
        pt or "juxing",
        round(float(l or 0), 2),
        round(float(w or 0), 2),
        round(float(h or 0), 2),
        mat[:64],
    )


def _has_dimoldb_match(item: dict, dm_index: dict) -> bool:
    l, w, h = ds._inventory_item_dims(item)
    if not (l and w and h):
        return False
    pt = item.get("product_type") or ""
    if pt == "changfang":
        pt = "juxing"
    fake = {"length": l, "width": w, "height": h, "product_type": pt, "name": item.get("name") or ""}
    hits = ds.match_dimoldb_for_inventory_item(fake, dm_index, infer_fn=ds.infer_type_class)
    return bool(hits)


def _display_spec(item: dict) -> str:
    name = (item.get("name") or item.get("spec") or "").strip()
    if name:
        return name
    l, w, h = ds._inventory_item_dims(item)
    mat = (item.get("material") or "").strip()
    if l and w and h:
        return f"{l}x{w}x{h}{mat}"
    return ""


def main() -> None:
    ap = argparse.ArgumentParser(description="导出成品有、刀模无的规格列表")
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=ROOT / "export_unmatched_dimoldb.txt",
        help="输出路径",
    )
    ap.add_argument("--also-km-map", action="store_true", help="同时写入 km_sku_map（SPEC:前缀）")
    args = ap.parse_args()

    inv_rows = load_inventory_finished()
    dim_rows = load_dimoldb()
    dm_index = ds.build_dim_match_index(dim_rows)

    # 按规格聚合库存
    grouped: dict[tuple, dict] = {}
    for it in inv_rows:
        key = _spec_key(it)
        if not key[1] or not key[2]:
            continue
        g = grouped.setdefault(
            key,
            {
                "item": it,
                "qty": 0,
            },
        )
        g["qty"] += int(it.get("qty") or 0)

    total = len(grouped)
    matched = 0
    unmatched: list[dict] = []
    for key, g in grouped.items():
        it = dict(g["item"])
        it["qty"] = g["qty"]
        if _has_dimoldb_match(it, dm_index):
            matched += 1
        else:
            unmatched.append(it)

    sq = [u for u in unmatched if (u.get("product_type") or "") in ("zhengsquare",)]
    rect = [u for u in unmatched if u not in sq]
    with_stock = [u for u in unmatched if int(u.get("qty") or 0) > 0]
    sq_stock = [u for u in sq if int(u.get("qty") or 0) > 0]

    lines = [
        "# 成品飞机盒 vs 刀模 — 未匹配导出",
        f"成品飞机盒规格总数\t{total}",
        f"刀模已有匹配（无需导出）\t{matched}",
        f"需导出（成品有、刀模无）\t{len(unmatched)}",
        f"其中 正方形\t{len(sq)}",
        f"其中 长方形\t{len(rect)}",
        f"其中 有库存的\t{len(with_stock)}",
        f"其中 零库存\t{len(unmatched) - len(with_stock)}",
        f"正方形有库存（优先）\t{len(sq_stock)}",
        "",
        "# 明细：类型\\t规格\\t库存",
    ]
    for u in sorted(unmatched, key=lambda x: (-int(x.get("qty") or 0), _display_spec(x))):
        pt = u.get("product_type") or "juxing"
        if pt == "changfang":
            pt = "长方形"
        elif pt == "zhengsquare":
            pt = "正方形"
        spec = _display_spec(u)
        qty = int(u.get("qty") or 0)
        lines.append(f"{pt}\t{spec}\t库存{qty}")

    out = args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已写入 {out}")
    print(f"未匹配 {len(unmatched)} / 总规格 {total}")

    if args.also_km_map:
        rows = []
        for u in unmatched:
            spec = _display_spec(u)
            l, w, h, mat = kms.parse_spec_alias_dims(spec)
            rows.append(
                {
                    "outer_id": f"SPEC:{spec[:120]}",
                    "spec_alias": spec,
                    "product_type": kms.normalize_product_type(
                        u.get("product_type") or "", l=l, w=w
                    ),
                    "length": l,
                    "width": w,
                    "height": h,
                    "dim_kind": "",
                    "material": mat or (u.get("material") or ""),
                    "km_title": "",
                }
            )
        n = kms.upsert_rows(rows)
        print(f"km_sku_map 写入 {n} 行")


if __name__ == "__main__":
    main()
