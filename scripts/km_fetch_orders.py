# -*- coding: utf-8 -*-
"""
快麦订单拉取脚本（服务器可直接运行）

- 淘系 tm/tb：erp.trade.outstock.simple.query（全账号，无需按店 userId）
- 1688 / 其他：erp.trade.list.query（单店 userId）
- Token：km_token.json 或环境变量 KM_APP_KEY / KM_APP_SECRET / KM_SESSION

用法:
  python scripts/km_fetch_orders.py --probe
  python scripts/km_fetch_orders.py --days 3 --out orders_sample.json
  python scripts/km_fetch_orders.py --outstock-only --days 1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env", override=False)
except ImportError:
    pass

import km_api  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="快麦订单拉取（outstock + list）")
    parser.add_argument("--days", type=int, default=3, help="回溯天数（按天切片）")
    parser.add_argument("--probe", action="store_true", help="连通性探测 JSON")
    parser.add_argument("--outstock-only", action="store_true", help="仅淘系 outstock")
    parser.add_argument("--list-only", action="store_true", help="仅 list.query 按店")
    parser.add_argument(
        "--out",
        type=str,
        default="",
        help="写入 JSON 文件（原始快麦行 + 缓存格式样例）",
    )
    args = parser.parse_args()

    if not km_api.km_configured():
        print("未配置：请在项目根目录配置 km_token.json 或 KM_* 环境变量", file=sys.stderr)
        return 2

    km_api.km_ensure_session(force=False)
    if args.probe:
        print(json.dumps(km_api.km_probe(), ensure_ascii=False, indent=2))
        return 0

    shops = km_api.km_shop_lookup(refresh=True)
    all_raw: list[dict] = []
    errors: list[dict] = []

    if not args.list_only:
        raw_o, err_o = km_api.km_fetch_trades_outstock(
            days_back=args.days,
            time_type="upd_time",
            status=None,
            source_filter=km_api.KM_TM_TB_SOURCES,
        )
        print(f"[outstock] 淘系 tm/tb: {len(raw_o)} 条, 告警 {len(err_o)}")
        all_raw.extend(raw_o)
        errors.extend(err_o)

    if not args.outstock_only:
        ids_1688 = [u for u, s in shops.items() if s.get("source") == "1688"]
        ids_other = [
            u
            for u, s in shops.items()
            if s.get("source") not in ("1688",) and s.get("source") not in km_api.KM_TM_TB_SOURCES
        ]
        for label, ids in (("1688", ids_1688), ("other", ids_other)):
            if not ids:
                continue
            raw, err = km_api.km_fetch_trades(
                args.days,
                time_type="pay_time",
                status=None if label == "1688" else km_api.KM_PENDING_STATUSES,
                shop_user_ids=ids,
            )
            print(f"[list] {label}: {len(raw)} 条, 告警 {len(err)}")
            all_raw.extend(raw)
            errors.extend(err)

    print(f"合计原始单: {len(all_raw)} 条")
    if errors:
        print("告警样例:", json.dumps(errors[:3], ensure_ascii=False))

    if args.out:
        cache_rows = [km_api.km_trade_to_cache_order(r, shops) for r in all_raw[:500]]
        payload = {
            "count_raw": len(all_raw),
            "errors": errors[:20],
            "sample_cache_orders": cache_rows[:20],
        }
        out_path = Path(args.out)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写入 {out_path}")

    return 0 if all_raw or not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
