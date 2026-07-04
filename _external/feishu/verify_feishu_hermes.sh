#!/bin/bash
# 飞书 / 小马哥 Hermes / OpenClaw 状态验收（在 87 应用机执行；部分项需 SSH 213/156）
set -euo pipefail

STABLE="${STABLE_DIR:-/www/feijihe/stable}"
PUBLIC="${PUBLIC_PROD:-https://feijihe.top}"

echo "========== 1. 87 Flask 飞书 Webhook =========="
for path in /api/webhook/feishu /api/webhook/kuaimai; do
  code=$(curl -s -o /tmp/wh.json -w "%{http_code}" --connect-timeout 10 "${PUBLIC}${path}" || echo "000")
  echo "  ${PUBLIC}${path} → HTTP ${code}"
  [ -f /tmp/wh.json ] && head -c 120 /tmp/wh.json && echo ""
done

echo ""
echo "========== 2. stable 是否含 feishu_dify.py =========="
for f in webhook_routes.py feishu_dify.py; do
  [ -f "${STABLE}/${f}" ] && echo "  OK ${STABLE}/${f}" || echo "  缺失 ${STABLE}/${f} → 需在 repo 执行 ./deploy.sh"
done

echo ""
echo "========== 3. .env 飞书/Dify（脱敏）=========="
grep -E '^(FEISHU_|DIFY_)' "${STABLE}/.env" 2>/dev/null | sed -E 's/(PASSWORD|TOKEN|SECRET|KEY)=.+/\\1=***/' || echo "  未配置 FEISHU_*（HTTP 回调模式需要）"

echo ""
echo "========== 4. Hermes 文档缓存目录（库存 Excel）=========="
for d in /home/admin/.hermes/cache/documents "${STABLE}/../.hermes/cache/documents"; do
  if [ -d "$d" ]; then
    n=$(find "$d" -maxdepth 1 -type f 2>/dev/null | wc -l)
    echo "  OK $d ($n 个文件)"
  else
    echo "  无 $d"
  fi
done

echo ""
echo "========== 5. 本机 3002 路由（应用机）=========="
if [ -f "${STABLE}/venv/bin/python3" ]; then
  (
    cd "$STABLE"
    source venv/bin/activate
    python3 "${STABLE%/*}/repo/scripts/verify_webhook_route.py" 2>&1 || true
  )
fi

echo ""
echo "========== 6. 156 OpenClaw（可选，需能 SSH 156）=========="
if command -v ssh &>/dev/null; then
  ssh -o ConnectTimeout=5 -o BatchMode=yes admin@172.16.0.94 \
    'ss -tlnp | grep -E "18789|18900" || echo "  156 未监听 18789/18900"; systemctl is-active openclaw 2>/dev/null || ps aux | grep -i openclaw | grep -v grep | head -2 || echo "  未找到 openclaw 进程"' \
    2>/dev/null || echo "  无法 SSH 156（可经 87 跳板）"
fi

echo ""
echo "========== 结论提示 =========="
echo "  · feishu webhook 404 → 87 上 cd /www/feijihe/repo && ./deploy.sh && systemctl restart sanyang-production"
echo "  · enabled:false → 补 stable/.env 的 FEISHU_* 后重启"
echo "  · 飞书后台仍指 213:18888 → 改 https://feijihe.top/api/webhook/feishu 或 156 长连接"
echo "  · 无 .hermes 目录 → 从 213 scp -r admin@213:/home/admin/.hermes /home/admin/"
