import requests, json
r = requests.post('http://api:5001/v1/chat-messages',
    headers={'Authorization': 'Bearer app-QPqaJURZfPW2xYAqq8UEfwr77RfMKAHx', 'Content-Type': 'application/json'},
    json={'inputs': {}, 'query': '1+1=?', 'response_mode': 'blocking', 'user': 'test'},
    timeout=30)
print(r.status_code)
print(r.text[:1000])
