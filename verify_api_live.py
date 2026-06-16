
import requests
import json
import time

def test_api():
    url = "http://127.0.0.1:5000/api/analyze"
    text = "ذهب الطالب الاي المدرسة"
    
    print(f"Sending request to {url}...")
    print(f"Text: {text}")
    
    try:
        response = requests.post(url, json={"text": text}, timeout=60)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Response JSON:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            if data['suggestions']:
                print("\n✅ Suggestions found!")
            else:
                print("\n⚠️ No suggestions found.")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    test_api()
