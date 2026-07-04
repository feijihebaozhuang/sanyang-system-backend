SELECT id, version, length(graph::text) AS graph_len, left(graph::text, 200) AS graph_preview
FROM workflows
WHERE app_id = '99e5ce7a-eab5-4a7f-a291-538d916cdfe9';
