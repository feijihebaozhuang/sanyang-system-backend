#!/usr/bin/env bash
set -euo pipefail
EMAIL="admin@local.com"
PASS="DifyAdmin2026"
KEY="sk-abaf056a56e745b396f0b7937ea503bb"

echo "==> reset admin password"
docker exec docker-api-1 bash -c "cd /app/api && PYTHONPATH=/app/api flask reset-password --email $EMAIL --new-password $PASS --password-confirm $PASS" </dev/null 2>&1 || true

echo "==> wait api"
for i in $(seq 1 20); do
  if curl -sf http://127.0.0.1/health 2>/dev/null | grep -q ok; then break; fi
  if docker exec docker-api-1 curl -sf http://localhost:5001/health 2>/dev/null | grep -q ok; then break; fi
  sleep 3
done

echo "==> login console"
TOKEN=$(curl -s -X POST "http://127.0.0.1/console/api/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\",\"remember_me\":true}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('access_token',''))" 2>/dev/null || echo "")

if [ -z "$TOKEN" ]; then
  echo "login failed, try workflow SQL only"
else
  echo "token ok (${#TOKEN} chars)"
  curl -s -X POST "http://127.0.0.1/console/api/workspaces/current/model-providers/deepseek" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"config\":{\"api_key\":\"$KEY\"}}" | head -c 400
  echo
fi

echo "==> workflow graph SQL"
docker cp /mnt/d/Desktop/sanyang-system/scripts/dify_publish_workflow.sql docker-db_postgres-1:/tmp/w.sql
docker exec -i docker-db_postgres-1 psql -U postgres -d dify -f /tmp/w.sql

echo "==> test chat API"
curl -s -X POST "http://127.0.0.1/v1/chat-messages" \
  -H "Authorization: Bearer app-QPqaJURZfPW2xYAqq8UEfwr77RfMKAHx" \
  -H "Content-Type: application/json" \
  -d '{"inputs":{},"query":"1+1=?","response_mode":"blocking","user":"bootstrap"}' | head -c 500
echo
