#!/bin/bash
# 87 一键：拉代码 → 部署 → 重置 admin → 修 Nginx → 验收 3003 登录
set -euo pipefail

REPO="${REPO:-/www/feijihe/repo}"
cd "$REPO"

echo "========== git pull + deploy.sh =========="
git fetch origin main
git pull origin main
bash "$REPO/deploy.sh"

echo ""
echo "========== 3003 admin 密码对齐 admin888 =========="
python3 "$REPO/scripts/reset_co_admin_3003.py" || true

echo ""
echo "========== Nginx 补丁 =========="
if [ "$(id -u)" -eq 0 ]; then
  bash "$REPO/scripts/ops/patch_feijihe_nginx_api_87.sh" || true
elif sudo -n true 2>/dev/null; then
  sudo bash "$REPO/scripts/ops/patch_feijihe_nginx_api_87.sh" || true
else
  echo "请 sudo bash $REPO/scripts/ops/patch_feijihe_nginx_api_87.sh"
fi

echo ""
echo "========== 本机 3003 =========="
curl -s -X POST "http://127.0.0.1:3003/api/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin888"}' | head -c 200
echo ""

echo ""
echo "========== 域名登录 API =========="
code=$(curl -s -o /tmp/sy_login_test.json -w "%{http_code}" \
  -X POST "https://feijihe.top/api/co/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin888"}' || echo "000")
echo "  POST https://feijihe.top/api/co/login → HTTP $code"
head -c 150 /tmp/sy_login_test.json 2>/dev/null; echo

code=$(curl -s -o /dev/null -w "%{http_code}" "https://feijihe.top/guanli/login" || echo "000")
echo "  GET  https://feijihe.top/guanli/login → HTTP $code (独立登录页)"

echo ""
echo "========== 服务端表单登录 POST =========="
code=$(curl -s -o /tmp/sy_form_login.html -w "%{http_code}" \
  -X POST "https://feijihe.top/guanli/login/submit" \
  -d "username=admin&password=admin888" || echo "000")
echo "  POST /guanli/login/submit → HTTP $code (期望 302 跳转 /guanli/)"
head -c 80 /tmp/sy_form_login.html 2>/dev/null; echo
