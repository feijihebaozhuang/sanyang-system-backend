#!/usr/bin/env bash
# One-shot: install DeepSeek plugin, set API key, publish workflow, smoke-test chat.
set -eu
ROOT=/mnt/d/Desktop/sanyang-system
KEY="${DEEPSEEK_API_KEY:-sk-abaf056a56e745b396f0b7937ea503bb}"
export DEEPSEEK_API_KEY="$KEY"

run_py() {
  local name="$1"
  docker cp "$ROOT/scripts/$name" "docker-api-1:/tmp/$name"
  docker exec docker-api-1 bash -c "cd /app/api && PYTHONPATH=/app/api python /tmp/$name"
}

echo "==> install DeepSeek plugin + credentials"
sed -i 's/\r$//' "$ROOT/scripts/dify_install_plugin2.py" "$ROOT/scripts/dify_set_deepseek_cred.py" 2>/dev/null || true
run_py dify_install_plugin2.py
run_py dify_set_deepseek_cred.py

echo "==> workflow graph"
docker cp "$ROOT/scripts/dify_publish_workflow.sql" docker-db_postgres-1:/tmp/w.sql
docker exec docker-db_postgres-1 psql -U postgres -d dify -f /tmp/w.sql

echo "==> chat smoke test"
curl -s -X POST 'http://127.0.0.1/v1/chat-messages' \
  -H 'Authorization: Bearer app-QPqaJURZfPW2xYAqq8UEfwr77RfMKAHx' \
  -H 'Content-Type: application/json' \
  --data-binary @"$ROOT/scripts/dify_chat_test.json" | head -c 400
echo
