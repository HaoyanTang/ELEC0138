import requests
from datetime import datetime, timedelta, timezone

url = "http://127.0.0.1:8001/lock/toggle"

headers = {
    "signature": "193a1f6cc602b3d69edb627ff6b0de435416ede69bdd99265bfadab45f733fcd",
    "Content-Type": "application/json"
}

now = int(datetime.now(timezone.utc).timestamp())

body = {
    "lock_id": 1,
    "timestamp": now
}

response = requests.post(url, headers=headers, json=body)

print("Status code:", response.status_code)
print("Response:", response.text)

