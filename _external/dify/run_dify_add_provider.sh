#!/usr/bin/env bash
set -euo pipefail
docker cp /mnt/d/Desktop/sanyang-system/scripts/dify_add_deepseek.py docker-api-1:/tmp/dify_add_deepseek.py
docker exec docker-api-1 bash -c 'cd /app/api && PYTHONPATH=/app/api python /tmp/dify_add_deepseek.py' 2>&1
curl -s -X POST "http://127.0.0.1/v1/chat-messages" \
  -H "Authorization: Bearer app-QPqaJURZfPW2xYAqq8UEfwr77RfMKAHx" \
  -H "Content-Type: application/json" \
  -d '{"inputs":{},"query":"1+1=?","response_mode":"blocking","user":"t"}' | head -c 600
echo
