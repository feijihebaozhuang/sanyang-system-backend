#!/usr/bin/env python3
from models.provider import Provider

print([c.name for c in Provider.__table__.columns])
