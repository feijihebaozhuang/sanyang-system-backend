#!/bin/bash
# 安装快麦定时同步（订单/SKU/库存）。需 root，小马哥在 87 执行一次。
set -euo pipefail

STABLE="${STABLE_DIR:-/www/feijihe/stable}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

install_unit() {
  local name="$1"
  local src="$SCRIPT_DIR/systemd/$name"
  [ -f "$src" ] || { echo "缺少 $src"; exit 1; }
  sed "s|/www/feijihe/stable|$STABLE|g" "$src" > "/etc/systemd/system/$name"
  echo "已写入 /etc/systemd/system/$name"
}

for unit in \
  sanyang-km-sync.service \
  sanyang-km-sync.timer \
  sanyang-km-sku-sync.service \
  sanyang-km-sku-sync.timer \
  sanyang-km-stock-sync.service \
  sanyang-km-stock-sync.timer; do
  install_unit "$unit"
done

systemctl daemon-reload
systemctl enable sanyang-km-sync.timer sanyang-km-sku-sync.timer sanyang-km-stock-sync.timer
systemctl start sanyang-km-sync.timer sanyang-km-sku-sync.timer sanyang-km-stock-sync.timer

echo "--- timer 状态 ---"
systemctl list-timers 'sanyang-km-*' --no-pager || true

echo "完成。首次 SKU 全量（可选，耗时长）:"
echo "  cd $STABLE && venv/bin/python3 scripts/km_sku_sync_once.py --mode full"
echo "刀模对账:"
echo "  venv/bin/python3 scripts/reconcile_dimoldb_km.py"
