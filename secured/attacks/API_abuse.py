import requests

url = "https://127.0.0.1:8001/lock/toggle"

data = {"lock_id": 1,
        "timestamp": 1} #the timestamp here is just for demo, it is not checked in a vulnerable system
response = requests.post(url, json=data, verify=False)
print(response.text)
print(response.status_code)