SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE '%provider%' ORDER BY 1;
SELECT column_name, data_type FROM information_schema.columns WHERE table_name='providers' ORDER BY ordinal_position;
SELECT id, provider_name, provider_type, is_valid, tenant_id FROM providers LIMIT 10;
SELECT id, name, mode, workflow_id FROM apps WHERE name ILIKE '%feishu%';
