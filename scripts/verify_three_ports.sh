#!/bin/bash
# 在 87 应用机验收 3001/3002/3003 本机与域名
set -euo pipefail

STABLE="${STABLE:-/www/feijihe/stable}"
cd "$STABLE" 2>/dev/null || cd "$(dirname "$0")/.."

echo "========== 本机端口 =========="
for p in 3001 3002 3003; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${p}/" 2>/dev/null || echo "000")
  echo "  :${p}/  HTTP ${code}"
done

echo ""
echo "========== 3003 登录 API（本机）=========="
curl -s -X POST "http://127.0.0.1:3003/api/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin888"}' | head -c 200
echo ""

echo ""
echo "========== 域名（若配置了 HTTPS）=========="
for url in \
  "https://zean.feijihe.top/" \
  "https://zean.feijihe.top/api/dashboard" \
  "https://feijihe.top/" \
  "https://guanli.feijihe.top/" \
  "https://guanli.feijihe.top/api/health" \
  "https://guanli.feijihe.top/api/login"
do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
  echo "  ${code}  ${url}"
done

echo ""
echo "========== guanli POST /api/login（应 200 + success，不能 403 HTML）=========="
curl -s -o /tmp/guanli_login.json -w "  guanli POST /api/login HTTP %{http_code}\n" \
  -X POST "https://guanli.feijihe.top/api/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin888"}' || true
head -c 150 /tmp/guanli_login.json 2>/dev/null; echo

echo ""
echo "========== guanli 经 feijihe 反代登录（绕过 guanli Nginx）=========="
curl -s -o /tmp/co_login.json -w "HTTP %{http_code}\n" \
  -X POST "https://feijihe.top/api/co/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin888"}' || true
head -c 150 /tmp/co_login.json 2>/dev/null; echo
