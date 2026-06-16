
import requests
import json

def test_analyze():
    url = "http://127.0.0.1:5000/api/analyze"
    payload = {
        "text": "الطلاب ذهبو الى المدرسة"
    }
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"Testing POST {url}")
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        print(f"POST Status Code: {response.status_code}")
        print(f"POST Response: {response.text}")
    except Exception as e:
        print(f"POST Error: {e}")

    print(f"\nTesting GET {url}")
    try:
        response = requests.get(url)
        print(f"GET Status Code: {response.status_code}")
        print(f"GET Response: {response.text}")
    except Exception as e:
        print(f"GET Error: {e}")

if __name__ == "__main__":
    test_analyze()
