SELECT id, app_id, version, marked_name, marked_comment FROM workflows WHERE app_id = '99e5ce7a-eab5-4a7f-a291-538d916cdfe9';

SELECT id, app_id, type, version FROM workflow_runs WHERE app_id = '99e5ce7a-eab5-4a7f-a291-538d916cdfe9' LIMIT 3;
