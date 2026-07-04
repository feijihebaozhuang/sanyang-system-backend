#!/usr/bin/env python3
"""Run inside docker-api-1: cd /app/api && python /tmp/dify_bootstrap_in_container.py"""
import json
import uuid

from extensions.ext_database import db
from core.helper import encrypter
from models import Account
from models.provider import Provider, ProviderCredential, ProviderModel
from models.workflow import Workflow

TENANT_ID = "dbb18920-b55e-42db-9148-18d20a0baa3a"
DEEPSEEK_KEY = "sk-abaf056a56e745b396f0b7937ea503bb"
WORKFLOW_ID = "cd4ef7de-3dc1-4a4a-8e60-0cfb6a6e7713"
APP_ID = "99e5ce7a-eab5-4a7f-a291-538d916cdfe9"


def ensure_deepseek_provider():
    cred_name = "deepseek-feishu-bot"
    existing = (
        db.session.query(ProviderCredential)
        .filter_by(tenant_id=TENANT_ID, provider_name="deepseek")
        .first()
    )
    payload = json.dumps({"api_key": DEEPSEEK_KEY})
    encrypted = encrypter.encrypt_token(tenant_id=TENANT_ID, token=payload)
    if existing:
        existing.encrypted_config = encrypted
        existing.credential_name = cred_name
        cred_id = existing.id
        print("updated provider_credentials deepseek")
    else:
        cred_id = str(uuid.uuid4())
        row = ProviderCredential(
            id=cred_id,
            tenant_id=TENANT_ID,
            provider_name="deepseek",
            credential_name=cred_name,
            encrypted_config=encrypted,
        )
        db.session.add(row)
        print("created provider_credentials deepseek")

    for model_name, model_type in [
        ("deepseek-chat", "llm"),
        ("deepseek-v4-flash", "llm"),
    ]:
        pm = (
            db.session.query(ProviderModel)
            .filter_by(
                tenant_id=TENANT_ID,
                provider_name="deepseek",
                model_name=model_name,
            )
            .first()
        )
        if not pm:
            db.session.add(
                ProviderModel(
                    id=str(uuid.uuid4()),
                    tenant_id=TENANT_ID,
                    provider_name="deepseek",
                    model_name=model_name,
                    model_type=model_type,
                    credential_id=cred_id,
                    is_valid=True,
                )
            )
    db.session.commit()
    print("deepseek models ok")


def publish_workflow_graph():
    graph = {
        "nodes": [
            {
                "id": "start",
                "type": "custom",
                "position": {"x": 80, "y": 280},
                "data": {
                    "title": "开始",
                    "type": "start",
                    "variables": [],
                },
            },
            {
                "id": "llm",
                "type": "custom",
                "position": {"x": 380, "y": 280},
                "data": {
                    "title": "LLM",
                    "type": "llm",
                    "model": {
                        "provider": "deepseek",
                        "name": "deepseek-chat",
                        "mode": "chat",
                        "completion_params": {"temperature": 0.7},
                    },
                    "prompt_template": [
                        {
                            "role": "system",
                            "text": "你是飞书助手，简洁友好地回答用户。",
                        }
                    ],
                    "memory": {"window": {"enabled": True, "size": 10}},
                    "context": {"enabled": False},
                    "vision": {"enabled": False},
                },
            },
            {
                "id": "answer",
                "type": "custom",
                "position": {"x": 680, "y": 280},
                "data": {
                    "title": "回复",
                    "type": "answer",
                    "answer": "{{#llm.text#}}",
                },
            },
        ],
        "edges": [
            {
                "id": "start-llm",
                "source": "start",
                "target": "llm",
                "sourceHandle": "source",
                "targetHandle": "target",
            },
            {
                "id": "llm-answer",
                "source": "llm",
                "target": "answer",
                "sourceHandle": "source",
                "targetHandle": "target",
            },
        ],
    }
    wf = db.session.query(Workflow).filter_by(id=WORKFLOW_ID).first()
    if not wf:
        print("workflow not found", WORKFLOW_ID)
        return
    wf.graph = json.dumps(graph, ensure_ascii=False)
    wf.version = "published"
    db.session.commit()
    print("workflow graph published, nodes=", len(graph["nodes"]))


if __name__ == "__main__":
    from app_factory import create_app

    app = create_app()
    if isinstance(app, tuple):
        app = app[0]
    with app.app_context():
        ensure_deepseek_provider()
        publish_workflow_graph()
    print("DONE")
