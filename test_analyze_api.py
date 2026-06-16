
import requests
import json

def test_analyze():
    url = "http://127.0.0.1:5001/api/analyze"
    payload = {
        "text": "الطلاب ذهبو الى المدرسة"
    }
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"Testing {url} with text: '{payload['text']}'")
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        print(f"Status Code: {response.status_code}")
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_analyze()
