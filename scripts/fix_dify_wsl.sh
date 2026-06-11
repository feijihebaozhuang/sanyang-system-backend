#!/usr/bin/env bash
# WSL 内修复 Dify：/home/dify 权限 + 等待 API 健康 + 测试 chat-messages
set -euo pipefail
COMPOSE_DIR="${DIFY_DOCKER_DIR:-/opt/services/dify/docker}"
API_KEY="${DIFY_API_KEY:-app-QPqaJURZfPW2xYAqq8UEfwr77RfMKAHx}"

cd "$COMPOSE_DIR"
echo "==> docker compose up -d"
docker compose up -d

echo "==> fix /home/dify in api containers"
sleep 15
for c in docker-api-1 docker-worker-1 docker-worker_beat-1 docker-api_websocket-1; do
  if docker ps -q -f "name=^${c}$" | grep -q .; then
    docker exec -u 0 "$c" sh -c 'mkdir -p /home/dify/.gunicorn && chown -R 1001:1001 /home/dify' 2>/dev/null || true
  fi
done

echo "==> wait api healthy"
for i in $(seq 1 30); do
  st=$(docker inspect docker-api-1 --format '{{.State.Health.Status}}' 2>/dev/null || echo unknown)
  echo "  [$i] health=$st"
  if [ "$st" = healthy ]; then
    break
  fi
  sleep 5
done

docker exec docker-api-1 curl -sf http://localhost:5001/health
echo ""

echo "==> test /v1/chat-messages"
code=$(curl -s -o /tmp/dify_chat.json -w "%{http_code}" -X POST http://127.0.0.1/v1/chat-messages \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"inputs":{},"query":"1+1=?","response_mode":"blocking","user":"fix-dify-test"}')
echo "HTTP $code"
head -c 600 /tmp/dify_chat.json
echo ""

if [ "$code" = "400" ]; then
  echo "==> app_unavailable: 尝试开启 enable_api / status"
  SQL_FIX="$(dirname "$0")/dify_enable_apps.sql"
  SQL_BOT="$(dirname "$0")/dify_fix_feishu_bot.sql"
  [ -f "$SQL_FIX" ] && docker exec -i docker-db_postgres-1 psql -U postgres -d dify < "$SQL_FIX" || true
  [ -f "$SQL_BOT" ] && docker exec -i docker-db_postgres-1 psql -U postgres -d dify < "$SQL_BOT" || true
  docker exec docker-db_postgres-1 psql -U postgres -d dify -t -c \
    "SELECT name, mode, enable_api, status FROM apps LIMIT 8;" 2>/dev/null || true
  echo "==> retry chat-messages"
  code2=$(curl -s -o /tmp/dify_chat2.json -w "%{http_code}" -X POST http://127.0.0.1/v1/chat-messages \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"inputs":{},"query":"1+1=?","response_mode":"blocking","user":"fix-dify-test"}')
  echo "HTTP $code2"
  head -c 600 /tmp/dify_chat2.json
  echo ""
fi

if [ "${code2:-$code}" != "200" ] && [ "${code2:-$code}" != "201" ]; then
  echo ""
  echo ">>> Dify 应用工作流图为空或模型未配置。请在浏览器打开 http://localhost"
  echo ">>> 1) 设置 -> 模型供应商 -> 添加 DeepSeek 或 Ollama"
  echo ">>> 2) 应用 Feishu Bot -> 工作流：开始 -> LLM -> 回复 -> 发布"
  echo ">>> 飞书桥接在 Dify 未就绪时会用 Ollama 回退（.env FEISHU_USE_OLLAMA_FALLBACK=true）"
fi
