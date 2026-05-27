#!/bin/bash
# 87 一键：拉代码 → 部署 → 修 guanli Nginx → 验收 3001/3002/3003
set -euo pipefail

REPO="${REPO:-/www/feijihe/repo}"
cd "$REPO"

echo "========== [1/4] git pull + deploy.sh =========="
git fetch origin main
git pull origin main
bash "$REPO/deploy.sh"

echo ""
echo "========== [2/4] 3003 admin 账号对齐 =========="
python3 "$REPO/scripts/reset_co_admin_3003.py" || true

echo ""
echo "========== [3/4] guanli Nginx（需 root/sudo）=========="
if [ "$(id -u)" -eq 0 ]; then
  bash "$REPO/scripts/ops/patch_guanli_nginx_87.sh" || echo "WARN: Nginx 补丁未完全成功，请手动改 guanli 配置"
elif sudo -n true 2>/dev/null; then
  sudo bash "$REPO/scripts/ops/patch_guanli_nginx_87.sh" || echo "WARN: Nginx 补丁未完全成功"
else
  echo "SKIP: 无 root，请手动在 guanli server 块 location / 前 include deploy/nginx-guanli-api-static.conf.include"
fi

echo ""
echo "========== [4/4] 验收 =========="
bash "$REPO/scripts/verify_three_ports.sh"

echo ""
echo "========== 3002 admin 登录后 role（本机）=========="
curl -s -c /tmp/sy3002.ck -b /tmp/sy3002.ck -X POST http://127.0.0.1:3002/api/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin888"}' | head -c 300
echo ""
curl -s -b /tmp/sy3002.ck http://127.0.0.1:3002/api/me | head -c 300
echo ""
