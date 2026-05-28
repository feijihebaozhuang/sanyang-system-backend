#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""刀模 km_mapping_code ↔ km_sku_map 对账报告。"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass


def main() -> int:
    ap = argparse.ArgumentParser(description="刀模 ↔ 快麦编码对账")
    ap.add_argument("--limit", type=int, default=50, help="每类样例条数")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    import dimoldb_store as ds
    import km_sku_map_store as kms
    from settings import get_db_config

    dims = ds.load_dimoldb(get_db_config, force=True)
    km_map = kms.load_all(force=True)

    no_code: list[dict] = []
    missing_in_km: list[dict] = []
    ok_match: list[dict] = []
    code_to_dims: dict[str, list[str]] = defaultdict(list)

    for d in dims:
        km_code = (d.get("km_mapping_code") or "").strip()
        name = d.get("name") or d.get("code") or ""
        if not km_code:
            no_code.append({"id": d.get("id"), "name": name, "code": d.get("code")})
            continue
        code_to_dims[km_code].append(name)
        if km_code not in km_map:
            missing_in_km.append(
                {"id": d.get("id"), "name": name, "km_mapping_code": km_code}
            )
        else:
            ok_match.append(
                {
                    "id": d.get("id"),
                    "name": name,
                    "km_mapping_code": km_code,
                    "km_title": km_map[km_code].get("km_title"),
                }
            )

    dup_codes = {k: v for k, v in code_to_dims.items() if len(v) > 1}
    orphan_km = [
        oid
        for oid in km_map
        if not any((d.get("km_mapping_code") or "").strip() == oid for d in dims)
    ]

    rep = {
        "dimoldb_total": len(dims),
        "km_sku_map_total": len(km_map),
        "with_km_code": len(dims) - len(no_code),
        "matched": len(ok_match),
        "missing_in_km_sku_map": len(missing_in_km),
        "no_km_mapping_code": len(no_code),
        "duplicate_km_codes": len(dup_codes),
        "orphan_km_codes_in_map": len(orphan_km),
        "samples": {
            "missing_in_km": missing_in_km[: args.limit],
            "no_code": no_code[: args.limit],
            "duplicate": dict(list(dup_codes.items())[: args.limit]),
            "orphan_km": orphan_km[: args.limit],
        },
    }

    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print("刀模 ↔ 快麦编码对账")
        print(f"  刀模总数: {rep['dimoldb_total']}")
        print(f"  km_sku_map: {rep['km_sku_map_total']}")
        print(f"  已填 km_mapping_code: {rep['with_km_code']}")
        print(f"  编码在 km_sku_map 命中: {rep['matched']}")
        print(f"  有码但 km_sku_map 缺失: {rep['missing_in_km_sku_map']}")
        print(f"  未填 km_mapping_code: {rep['no_km_mapping_code']}")
        print(f"  一码多刀模: {rep['duplicate_km_codes']}")
        print(f"  km_sku_map 无刀模对应: {rep['orphan_km_codes_in_map']}")
        if missing_in_km:
            print("\n缺失样例（前5）:")
            for x in missing_in_km[:5]:
                print(f"  {x['km_mapping_code']} ← 刀模 {x['name']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
