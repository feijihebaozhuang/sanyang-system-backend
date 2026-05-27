#!/bin/bash
# 87：为 feijihe.top / zean.feijihe.top 插入 /api/ 反代（修复 Unexpected token '<'）
set -euo pipefail

REPO="${REPO:-/www/feijihe/repo}"
FEIJ="${REPO}/deploy/nginx-feijihe-api.conf.include"
ZEAN="${REPO}/deploy/nginx-zean-api.conf.include"
GUANLI="${REPO}/deploy/nginx-guanli-api-static.conf.include"

patch_server() {
  local domain="$1"
  local inc="$2"
  local marker
  marker=$(basename "$inc")
  local found=0 patched=0
  for dir in /etc/nginx /etc/nginx/conf.d /etc/nginx/sites-enabled /etc/nginx/sites-available; do
    [ -d "$dir" ] || continue
    while IFS= read -r -d '' f; do
      grep -q "$domain" "$f" || continue
      found=1
      if grep -q "$marker" "$f"; then
        echo "OK 已包含 $marker: $f"
        continue
      fi
      bak="${f}.bak.$(date +%Y%m%d%H%M%S)"
      cp -a "$f" "$bak"
      awk -v inc="include $inc;" -v domain="$domain" '
        BEGIN { done=0 }
        $0 ~ "server_name" && index($0, domain) { in_srv=1 }
        in_srv && /location[[:space:]]+\// && !done {
          print "    " inc
          done=1
        }
        { print }
        END { if (!done) exit 2 }
      ' "$f" > "${f}.new" || {
        echo "WARN: 无法自动插入 $f，请手动在 location / 前 include $inc"
        rm -f "${f}.new"
        continue
      }
      mv "${f}.new" "$f"
      patched=1
      echo "PATCHED: $f (backup $bak)"
    done < <(find "$dir" -type f -name '*.conf' -print0 2>/dev/null)
  done
  [ "$found" -eq 1 ] || echo "WARN: 未找到 server_name $domain"
  return 0
}

[ -f "$FEIJ" ] && [ -f "$ZEAN" ] || { echo "缺少 nginx include 文件，请先 git pull"; exit 1; }

patch_server "feijihe.top" "$FEIJ"
patch_server "zean.feijihe.top" "$ZEAN"
if [ -f "$GUANLI" ]; then
  bash "${REPO}/scripts/ops/patch_guanli_nginx_87.sh" || true
fi

nginx -t
systemctl reload nginx
echo "Nginx 已 reload"

echo "验收 JSON（应含 summary 或 success，不能是 HTML）："
curl -s "http://127.0.0.1:3002/api/dashboard" | head -c 80; echo
curl -s "http://127.0.0.1:3001/api/dashboard" 2>/dev/null | head -c 80; echo
curl -s -o /dev/null -w "feijihe /api/dashboard HTTP %{http_code}\n" "https://feijihe.top/api/dashboard" || true
curl -s -o /dev/null -w "zean /api/dashboard HTTP %{http_code}\n" "https://zean.feijihe.top/api/dashboard" || true
