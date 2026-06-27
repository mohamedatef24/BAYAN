import requests
import json

resp = requests.post("http://127.0.0.1:8000/api/v1/analyze", json={"text": "الولاد يلعبون بالشاروع"})
print(json.dumps(resp.json(), ensure_ascii=False))
