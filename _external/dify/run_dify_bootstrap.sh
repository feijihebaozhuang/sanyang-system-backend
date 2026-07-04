#!/usr/bin/env bash
set -euo pipefail
docker cp /mnt/d/Desktop/sanyang-system/scripts/dify_bootstrap_in_container.py docker-api-1:/tmp/dify_bootstrap.py
docker exec docker-api-1 bash -c 'cd /app/api && PYTHONPATH=/app/api python << "PY"
from app import app
ctx = app.app_context()
ctx.push()
exec(open("/tmp/dify_bootstrap.py").read().split("if __name__")[0])
ensure_deepseek_provider()
publish_workflow_graph()
print("DONE")
PY'
