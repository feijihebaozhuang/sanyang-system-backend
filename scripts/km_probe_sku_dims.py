#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""探测快麦 SKU 商品档案 x/y/z（例：51714）。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass

import km_api  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="快麦 SKU 尺寸探测 erp.item.single.sku.get")
    ap.add_argument("code", help="规格商家编码 skuOuterId，如 51714")
    ap.add_argument("--sys-sku-id", default="", help="可选 sysSkuId")
    args = ap.parse_args()
    if not km_api.km_configured():
        print("未配置 KM_* 或 km_token.json", file=sys.stderr)
        return 2
    km_api.km_ensure_session()
    sku = km_api.km_item_single_sku_get(
        sku_outer_id=args.code.strip(),
        sys_sku_id=args.sys_sku_id.strip() or None,
    )
    dims = km_api.km_product_dims_from_sku_record(sku)
    print(
        json.dumps(
            {
                "skuOuterId": args.code.strip(),
                "raw_sku": sku,
                "production_dims": dims,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if dims else 1


if __name__ == "__main__":
    raise SystemExit(main())
