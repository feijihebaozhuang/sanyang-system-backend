#!/bin/bash
# 安装/更新 systemd 单元（需 root）。安装后由 deploy.sh 自动 systemctl restart。
set -euo pipefail

STABLE="${STABLE_DIR:-/www/feijihe/stable}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

for unit in sanyang-cs.service sanyang-production.service; do
  src="$SCRIPT_DIR/systemd/$unit"
  [ -f "$src" ] || { echo "缺少 $src"; exit 1; }
  sed "s|/www/feijihe/stable|$STABLE|g" "$src" > "/etc/systemd/system/$unit"
  echo "已写入 /etc/systemd/system/$unit"
done

systemctl daemon-reload
systemctl enable sanyang-cs.service sanyang-production.service
systemctl restart sanyang-cs.service sanyang-production.service
systemctl --no-pager status sanyang-cs.service sanyang-production.service || true
echo "完成：ExecStart 使用 $STABLE/venv/bin/python3"
