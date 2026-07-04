#!/usr/bin/env bash
set -eucurl -s -X POST 'http://127.0.0.1/v1/chat-messages' \
  -H 'Authorization: Bearer app-QPqaJURZfPW2xYAqq8UEfwr77RfMKAHx' \
  -H 'Content-Type: application/json' \
  -d '{"inputs":{},"query":"1+1=?","response_mode":"blocking","user":"t"}'
