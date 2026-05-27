#!/bin/bash
# 87：修复 zean.feijihe.top 拒绝连接 / 502（3001 + Nginx 全站反代）
set -euo pipefail

REPO="${REPO:-/www/feijihe/repo}"
STABLE="${STABLE:-/www/feijihe/stable}"

echo "========== [1/5] 拉代码 + 部署 3001 =========="
cd "$REPO"
git fetch origin main
git pull origin main
bash "$REPO/deploy.sh"

echo ""
echo "========== [2/5] 3001 进程 =========="
if systemctl is-active sanyang-cs.service &>/dev/null; then
  systemctl restart sanyang-cs.service
  sleep 2
  systemctl status sanyang-cs.service --no-pager | head -15
else
  echo "WARN: 无 systemd，请手动确认 3001 在跑"
fi

code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:3001/" 2>/dev/null || echo "000")
echo "  本机 http://127.0.0.1:3001/ → HTTP $code"
if [ "$code" = "000" ]; then
  echo "ERROR: 3001 无响应，请查 journalctl -u sanyang-cs -n 50"
  exit 1
fi

echo ""
echo "========== [3b/5] zean server 根路径反代 3001 =========="
_zean_fix_root() {
  local f="$1"
  grep -q 'zean\.feijihe\.top' "$f" || return 0
  if grep -q 'proxy_pass http://127.0.0.1:3001' "$f" && grep -q 'location /' "$f"; then
    echo "OK 已有 3001 反代: $f"
    return 0
  fi
  echo "WARN: 请检查 $f 中 location / 是否反代 127.0.0.1:3001（参考 deploy/nginx-zean.example.conf）"
}
for dir in /etc/nginx/conf.d /etc/nginx/sites-enabled /etc/nginx/sites-available; do
  [ -d "$dir" ] || continue
  while IFS= read -r -d '' f; do
    _zean_fix_root "$f"
  done < <(find "$dir" -maxdepth 1 -type f -name '*.conf' -print0 2>/dev/null)
done

echo ""
echo "========== [3/5] Nginx include 补丁 =========="
if [ "$(id -u)" -eq 0 ]; then
  bash "$REPO/scripts/ops/patch_feijihe_nginx_api_87.sh"
elif sudo -n true 2>/dev/null; then
  sudo bash "$REPO/scripts/ops/patch_feijihe_nginx_api_87.sh"
else
  echo "请 sudo bash $REPO/scripts/ops/patch_feijihe_nginx_api_87.sh"
fi

echo ""
echo "========== [4/5] 域名验收 =========="
for url in "https://zean.feijihe.top/" "https://zean.feijihe.top/api/dashboard"; do
  c=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
  echo "  $c  $url"
done

echo ""
echo "========== [5/5] 端口监听 =========="
ss -tlnp 2>/dev/null | grep -E ':3001|:443|:80' || netstat -tlnp 2>/dev/null | grep -E '3001|443|80' || true

echo ""
echo "完成。外网请用 https://zean.feijihe.top（不要直连 :3001）"
