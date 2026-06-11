#!/usr/bin/env bash
set -e
for i in $(seq 1 15); do
  st=$(docker inspect docker-api-1 --format "{{.State.Health.Status}}" 2>/dev/null)
  if [ -z "$st" ]; then st=unknown; fi
  echo "  [$i] health=$st"
  if [ "$st" = healthy ]; then break; fi
  sleep 3
done
echo "final=$st"
st=$(docker inspect docker-api-1 --format "{{.State.Health.Status}}" 2>/dev/null)
if [ "$st" = healthy ]; then
  echo "Dify is healthy"
  curl -sf http://localhost:5001/health && echo ""
else
  echo "Dify not healthy after wait"
fi
