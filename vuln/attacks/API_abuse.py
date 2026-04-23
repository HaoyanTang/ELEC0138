import requests

url = "http://127.0.0.1:8001/lock/toggle"

data = {"lock_id": 1,
        "timestamp": 1} #the timestamp here is just for demo, it is not checked in a vulnerable system
response = requests.post(url, json=data)
print(response.text)