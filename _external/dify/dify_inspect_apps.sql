SELECT a.id, a.name, a.mode, a.enable_api, a.status, a.app_model_config_id, a.workflow_id
FROM apps a;

SELECT amc.id, amc.app_id, amc.provider, amc.model_id
FROM app_model_configs amc
LIMIT 5;
