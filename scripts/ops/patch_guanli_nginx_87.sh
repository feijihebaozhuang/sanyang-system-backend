#!/bin/bash
# 在 87 上为 guanli.feijihe.top 插入 API/static 放行 include（解决 POST /api/login 403）
set -euo pipefail

INCLUDE_LINE='include /www/feijihe/repo/deploy/nginx-guanli-api-static.conf.include;'
MARKER='nginx-guanli-api-static.conf.include'

if [ ! -f "/www/feijihe/repo/deploy/nginx-guanli-api-static.conf.include" ]; then
  echo "ERROR: 缺少 $MARKER，请先 git pull"
  exit 1
fi

found=0
patched=0
search_dirs=(/etc/nginx /etc/nginx/conf.d /etc/nginx/sites-enabled /etc/nginx/sites-available)

for dir in "${search_dirs[@]}"; do
  [ -d "$dir" ] || continue
  while IFS= read -r -d '' f; do
    grep -q 'guanli\.feijihe\.top' "$f" || continue
    found=1
    if grep -q "$MARKER" "$f"; then
      echo "OK 已包含 include: $f"
      continue
    fi
    bak="${f}.bak.$(date +%Y%m%d%H%M%S)"
    cp -a "$f" "$bak"
    awk -v inc="$INCLUDE_LINE" '
      BEGIN { done=0 }
      /server_name[[:space:]]+guanli\.feijihe\.top/ { in_srv=1 }
      in_srv && /location[[:space:]]+\// && !done {
        print "    " inc
        done=1
      }
      { print }
      END {
        if (!done) exit 2
      }
    ' "$f" > "${f}.new" || {
      echo "WARN: 无法在 $f 自动插入（请手动在 location / 前加 include）"
      rm -f "${f}.new"
      continue
    }
    mv "${f}.new" "$f"
    patched=1
    echo "PATCHED: $f (backup $bak)"
  done < <(find "$dir" -type f \( -name '*.conf' -o -name 'guanli*' \) -print0 2>/dev/null)
done

if [ "$found" -eq 0 ]; then
  echo "WARN: 未找到含 guanli.feijihe.top 的 Nginx 配置，请手动参考 deploy/nginx-guanli.example.conf"
  exit 2
fi

if [ "$patched" -eq 1 ]; then
  nginx -t
  systemctl reload nginx
  echo "Nginx 已 reload"
fi

echo "验收:"
curl -s -o /dev/null -w "  guanli POST /api/login → HTTP %{http_code}\n" \
  -X POST "https://guanli.feijihe.top/api/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin888"}' || true
