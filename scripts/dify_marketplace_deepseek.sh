#!/usr/bin/env bash
set -eu
docker exec docker-api-1 curl -s -X POST 'https://marketplace.dify.ai/api/v1/plugins/batch' \
  -H 'Content-Type: application/json' \
  -H 'X-Dify-Version: 1.14.0' \
  -d '{"plugin_ids":["langgenius/deepseek/deepseek"]}' > /tmp/deepseek_batch.json
docker exec docker-api-1 cat /tmp/deepseek_batch.json
echo
docker exec docker-api-1 curl -s 'https://marketplace.dify.ai/api/v1/dist/plugins/manifest.json' \
  -H 'X-Dify-Version: 1.14.0' -o /tmp/manifest.json
docker exec docker-api-1 python3 -c "
import json
with open('/tmp/manifest.json') as f:
    d=json.load(f)
for p in d.get('plugins',[]):
    if 'deepseek' in json.dumps(p).lower():
        print(p.get('plugin_id'), p.get('latest_package_identifier',''))
        break
else:
    print('not in manifest')
"
