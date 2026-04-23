import requests

URL = "http://127.0.0.1:8001/lock/toggle?username=tang"

body = {
    "lock_id": 1,
    "timestamp": 1776896748
}

headers = {
    "Content-Type": "application/json"
}

def replay_request():
    response = requests.post(URL, json=body, headers=headers, timeout=5)
    print(f"status:", response.status_code)
    print(f"body:", response.text)

if __name__ == "__main__":
    replay_request()
