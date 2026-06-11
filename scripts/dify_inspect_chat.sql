SELECT column_name FROM information_schema.columns WHERE table_name='app_model_configs' ORDER BY 1;
SELECT id, app_id, provider, model_id FROM app_model_configs LIMIT 5;
