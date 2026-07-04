-- 修复 Dify 应用 API 不可用：开启 enable_api，工作流类应用标记为 normal
UPDATE apps SET enable_api = true WHERE enable_api IS DISTINCT FROM true;
UPDATE apps SET status = 'normal' WHERE status IS NULL OR status = '';
