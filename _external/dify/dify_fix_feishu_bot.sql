-- Feishu Bot：有 workflow_id 但 mode=chat 且无 app_model_config → API 报 app_unavailable
UPDATE apps
SET mode = 'advanced-chat'
WHERE name = 'Feishu Bot'
  AND workflow_id IS NOT NULL
  AND app_model_config_id IS NULL;
