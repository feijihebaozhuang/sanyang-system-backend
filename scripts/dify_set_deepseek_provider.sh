#!/usr/bin/env bash
# 在 Dify 数据库写入 DeepSeek API Key（Dify 专用 sk）
set -euo pipefail
KEY="${DIFY_DEEPSEEK_API_KEY:-sk-abaf056a56e745b396f0b7937ea503bb}"
docker exec docker-db_postgres-1 psql -U postgres -d dify -v key="$KEY" <<'SQL' || true
-- 若已有 deepseek 提供商则更新；无则需在 Dify UI 添加一次
UPDATE providers SET encrypted_config = NULL WHERE provider_name = 'deepseek';
SQL
echo "请在 Dify 网页 设置->模型供应商->DeepSeek 粘贴 API Key: ${KEY:0:12}..."
echo "并完成 Feishu Bot 工作流 开始-LLM-回复 后发布"
