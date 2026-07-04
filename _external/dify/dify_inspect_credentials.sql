SELECT id, name FROM tenants;
SELECT column_name FROM information_schema.columns WHERE table_name='provider_credentials' ORDER BY 1;
SELECT * FROM provider_credentials LIMIT 3;
SELECT column_name FROM information_schema.columns WHERE table_name='provider_models' ORDER BY 1;
SELECT id, length(graph::text) glen, left(graph::text, 500) FROM workflows WHERE id='cd4ef7de-3dc1-4a4a-8e60-0cfb6a6e7713';
