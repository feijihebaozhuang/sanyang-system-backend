UPDATE workflows
SET graph = '{
  "nodes": [
    {
      "id": "start",
      "type": "custom",
      "position": {"x": 80, "y": 280},
      "data": {
        "title": "开始",
        "type": "start",
        "variables": []
      }
    },
    {
      "id": "llm",
      "type": "custom",
      "position": {"x": 380, "y": 280},
      "data": {
        "title": "LLM",
        "type": "llm",
        "model": {
          "provider": "langgenius/deepseek/deepseek",
          "name": "deepseek-chat",
          "mode": "chat",
          "completion_params": {"temperature": 0.7}
        },
        "prompt_template": [
          {"role": "system", "text": "你是飞书助手，简洁回答。"}
        ],
        "memory": {"window": {"enabled": true, "size": 10}},
        "context": {"enabled": false},
        "vision": {"enabled": false}
      }
    },
    {
      "id": "answer",
      "type": "custom",
      "position": {"x": 680, "y": 280},
      "data": {
        "title": "回复",
        "type": "answer",
        "answer": "{{#llm.text#}}"
      }
    }
  ],
  "edges": [
    {"id": "start-llm", "source": "start", "target": "llm", "sourceHandle": "source", "targetHandle": "target"},
    {"id": "llm-answer", "source": "llm", "target": "answer", "sourceHandle": "source", "targetHandle": "target"}
  ]
}'::json,
    version = 'published'
WHERE id = 'cd4ef7de-3dc1-4a4a-8e60-0cfb6a6e7713';

UPDATE apps SET enable_api = true, status = 'normal' WHERE id = '99e5ce7a-eab5-4a7f-a291-538d916cdfe9';
