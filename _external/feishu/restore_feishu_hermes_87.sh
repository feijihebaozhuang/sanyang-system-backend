#!/bin/bash
# 在 87 应用机执行：部署飞书 webhook + 同步 Hermes 缓存 + 重启
# 用法:
#   bash restore_feishu_hermes_87.sh
#   OLD_HOST=admin@8.138.10.213 bash restore_feishu_hermes_87.sh   # 同时从 213 拉 .hermes
set -euo pipefail

REPO="${REPO_DIR:-/www/feijihe/repo}"
STABLE="${STABLE_DIR:-/www/feijihe/stable}"
OLD_HOST="${OLD_HOST:-}"

echo "[1/5] git pull + deploy（同步 feishu_dify.py / webhook_routes.py）..."
cd "$REPO"
git pull origin main
./deploy.sh

echo "[2/5] 从 213 拉 Hermes 文档缓存（可选）..."
if [ -n "$OLD_HOST" ]; then
  mkdir -p /home/admin/.hermes/cache/documents
  scp -r "${OLD_HOST}:/home/admin/.hermes/" /home/admin/ 2>/dev/null || \
    echo "WARN: scp .hermes 失败，请手动从 213 拷贝 /home/admin/.hermes"
  chown -R admin:admin /home/admin/.hermes 2>/dev/null || true
else
  echo "  跳过（设 OLD_HOST=admin@8.138.10.213 可从 213 拉取）"
fi

echo "[3/5] 检查 .env 飞书配置..."
if ! grep -q '^FEISHU_DIFY_ENABLED=true' "$STABLE/.env" 2>/dev/null; then
  echo "WARN: stable/.env 未启用 FEISHU_DIFY_ENABLED"
  echo "  若飞书用 HTTP 回调，需追加（App 凭证从 213 旧 .env 或飞书后台复制）："
  echo "    FEISHU_DIFY_ENABLED=true"
  echo "    FEISHU_APP_ID=cli_xxx"
  echo "    FEISHU_APP_SECRET=xxx"
  echo "    DIFY_API_BASE=..."
  echo "    DIFY_API_KEY=app-xxx"
fi

echo "[4/5] 重启生产端..."
sudo systemctl restart sanyang-production
sleep 2
systemctl is-active sanyang-production

echo "[5/5] 探活..."
curl -s "https://feijihe.top/api/webhook/feishu" | head -c 200
echo ""
curl -s "https://feijihe.top/api/webhook/kuaimai" | head -c 120
echo ""

echo ""
echo "========== 飞书后台（必做其一）=========="
echo "A) HTTP 回调（原 213:18888 迁到 87）："
echo "   https://open.feishu.cn/app → 你的机器人 App → 事件与回调"
echo "   订阅方式：将事件发送至开发者服务器"
echo "   请求地址：https://feijihe.top/api/webhook/feishu"
echo "   事件：im.message.receive_v1"
echo ""
echo "B) OpenClaw 长连接（机器人在 156）："
echo "   订阅方式：使用长连接接收事件（不要填 213 IP）"
echo "   在 156 执行：openclaw gateway restart 或 systemctl restart openclaw"
echo ""
echo "改完后在飞书 @机器人 发「测试」验收。"
