#!/bin/bash
# 在应用机 8.166.132.87 执行，导出 permission_data 并 scp 到 156
set -euo pipefail

STABLE="${STABLE_DIR:-/www/feijihe/stable}"
TARGET_HOST="${TARGET_HOST:-admin@8.163.107.156}"
TARGET_PATH="${TARGET_PATH:-/opt/sanyang-config/permission_data.json}"

cd "$STABLE"
python3 -c "
import json
from pathlib import Path
d = json.loads(Path('data.json').read_text(encoding='utf-8'))
pd = d.get('permission_data', {})
Path('/tmp/permission_data.json').write_text(
    json.dumps(pd, ensure_ascii=False, indent=2), encoding='utf-8')
print('exported keys:', list(pd.keys())[:8], '...')
"

scp /tmp/permission_data.json "${TARGET_HOST}:${TARGET_PATH}"
echo "已上传到 ${TARGET_HOST}:${TARGET_PATH}"
echo "下一步: 在 156 执行 install_permission_vault_156.sh"
