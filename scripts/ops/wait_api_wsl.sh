#!/usr/bin/env bash
for i in 1 2 3 4 5 6 7 8 9 10; do
  st=$(docker inspect docker-api-1 --format '{{.State.Health.Status}}' 2>/dev/null)
  echo "[$i] $st"
  if [ "$st" = healthy ]; then
    curl -s http://127.0.0.1/v1/info | head -c 200
    echo ""
    break
  fi
  sleep 5
done
