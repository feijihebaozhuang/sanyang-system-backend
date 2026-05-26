#!/bin/bash
# 在 feijihe.top Nginx 上启用 /api/mp/ → 3003，解决小程序绑定 HTTP 405
set -euo pipefail

REPO_DIR="${REPO_DIR:-/www/feijihe/repo}"
INCLUDE_SRC="$REPO_DIR/deploy/nginx-feijihe-mp.conf.include"
INCLUDE_DST="/etc/nginx/conf.d/feijihe-mp-api.include"
MARKER="# sanyang-mp-api-proxy"

if [ ! -f "$INCLUDE_SRC" ]; then
  echo "缺少 $INCLUDE_SRC，请先 git pull"
  exit 1
fi

cp -f "$INCLUDE_SRC" "$INCLUDE_DST"
echo "已安装 $INCLUDE_DST"

# 在 feijihe.conf 中 include（若尚未添加）
FEIJIH_CONF=""
for f in /etc/nginx/conf.d/feijihe.conf /etc/nginx/sites-enabled/feijihe.conf /etc/nginx/nginx.conf; do
  [ -f "$f" ] && FEIJIH_CONF="$f" && break
done

if [ -z "$FEIJIH_CONF" ]; then
  echo "未找到 feijihe nginx 配置，请手动在 feijihe.top 的 server { } 内添加："
  echo "  include $INCLUDE_DST;"
  exit 0
fi

if grep -q "$MARKER" "$FEIJIH_CONF" 2>/dev/null || grep -q "feijihe-mp-api.include" "$FEIJIH_CONF" 2>/dev/null; then
  echo "feijihe nginx 已包含 mp 代理"
else
  # 在第一个 server { 块末尾 location / 之前插入较复杂，简单追加 include 到 server 内
  sed -i "/server_name.*feijihe.top/i\\    include $INCLUDE_DST; $MARKER" "$FEIJIH_CONF" 2>/dev/null || {
    echo "请手动编辑 $FEIJIH_CONF ，在 feijihe.top 的 server 块中加入："
    echo "    include $INCLUDE_DST;"
  }
fi

nginx -t
systemctl reload nginx

echo "验证 POST /api/mp/cs/wx/login ..."
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "https://feijihe.top/api/mp/cs/wx/login" \
  -H "Content-Type: application/json" -d '{"code":"test"}' || echo "000")
echo "HTTPS 返回: $code (期望 400/401/200，不要 405/404)"

if [ "$code" = "405" ] || [ "$code" = "404" ]; then
  echo "仍异常，请确认 sanyang-customer-order.service 在运行: systemctl status sanyang-customer-order"
  exit 1
fi

echo "OK"
