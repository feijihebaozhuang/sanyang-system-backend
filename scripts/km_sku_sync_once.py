#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快麦商品编码 → km_sku_map 定时同步（systemd / cron）。"""
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


def main() -> int:
    ap = argparse.ArgumentParser(description="快麦 SKU → km_sku_map")
    ap.add_argument(
        "--mode",
        choices=("incremental", "full", "enrich"),
        default="incremental",
    )
    ap.add_argument("--hours", type=int, default=0, help="增量回溯小时（0=环境变量）")
    ap.add_argument("--resume", action="store_true", help="全量续跑")
    ap.add_argument("--max-pages", type=int, default=0)
    args = ap.parse_args()

    import km_sku_sync as kss

    if args.mode == "full":
        rep = kss.sync_full(resume=args.resume, max_pages=args.max_pages or None)
    elif args.mode == "enrich":
        rep = kss.enrich_unknown_skus_from_orders()
    else:
        rep = kss.sync_incremental(hours_back=args.hours or None)
        if rep.get("ok") and __import__("os").getenv("KM_SKU_ENRICH_AFTER_SYNC", "1") != "0":
            enrich = kss.enrich_unknown_skus_from_orders()
            rep["enrich"] = enrich

    print(json.dumps(rep, ensure_ascii=False, indent=2, default=str))
    return 0 if rep.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
