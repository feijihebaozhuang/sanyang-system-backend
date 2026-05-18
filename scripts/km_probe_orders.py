# -*- coding: utf-8 -*-
"""快麦订单探测：按店 userId + 驼峰参数（见 docs/kuaimai-api-requirements.md）。"""
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
    parser = argparse.ArgumentParser(description="快麦 erp.trade.list.query 探测")
    parser.add_argument("--days", type=int, default=3, help="回溯天数")
    parser.add_argument("--probe", action="store_true", help="输出 km_probe() JSON")
    args = parser.parse_args()

    if not km_api.km_configured():
        print("未配置：KM_* 或 km_token.json", file=sys.stderr)
        return 2

    if args.probe:
        print(json.dumps(km_api.km_probe(), ensure_ascii=False, indent=2))
        return 0

    km_api.km_ensure_session()
    orders, errors = km_api.km_fetch_trades(days_back=args.days, time_type="pay_time")
    print(f"合计: {len(orders)} 条，告警: {len(errors)}")
    if errors:
        print(json.dumps(errors[:5], ensure_ascii=False, indent=2))
    if orders:
        o = km_api.km_trade_to_cache_order(orders[0])
        print("首单缓存格式:", json.dumps(o, ensure_ascii=False)[:800])
    return 0 if orders or not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
