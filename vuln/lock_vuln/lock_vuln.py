from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import json
import os

PAIRING_CODE = "88888888"
LOCK_ID = 1
LOCK_STATE_FILE = "lock_state.json"


class Lock(BaseModel):
    lock_id: int
    action: str
    password: str
    timestamp: int


class ToggleLock(BaseModel):
    lock_id: int
    timestamp: int


app = FastAPI()


def save_lock_state(state: dict):
    with open(LOCK_STATE_FILE, "w") as f:
        json.dump(state, f)


def load_lock_state():
    with open(LOCK_STATE_FILE, "r") as f:
        return json.load(f)


def init_lock_state():
    state = {
        "status": "Locked"
    }
    with open(LOCK_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


if not os.path.isfile(LOCK_STATE_FILE):
    init_lock_state()


@app.post("/lock/pair")
async def pair(
    lock: Lock,
):
    # 脆弱点：
    # 1. 不校验 signature
    # 2. 不校验 timestamp freshness
    # 3. 只要 lock_id 和 pairing code 对，就接受请求

    if str(LOCK_ID) != str(lock.lock_id):
        raise HTTPException(
            status_code=400,
            detail="Lock ID mismatch",
        )

    if lock.password != PAIRING_CODE:
        raise HTTPException(
            status_code=400,
            detail="Pairing code mismatch",
        )

    lock_state = load_lock_state()["status"]
    timestamp = int(datetime.now(timezone.utc).timestamp())
    response_data = {
        "lock_id": LOCK_ID,
        "status": "success",
        "action": lock.action,
        "lock_state": lock_state,
        "timestamp": timestamp,
    }

    # 脆弱点：不返回 signature，backend 也不会验
    return {
        "data": response_data
    }


@app.post("/lock/toggle")
async def toggle_lock(
    lock: ToggleLock,
):
    if str(LOCK_ID) != str(lock.lock_id):
        raise HTTPException(
            status_code=400,
            detail="Lock ID mismatch",
        )

    current_state = load_lock_state()["status"]

    if current_state == "Locked":
        save_lock_state(state={"status": "Unlocked"})
    elif current_state == "Unlocked":
        save_lock_state(state={"status": "Locked"})

    lock_state = load_lock_state()["status"]
    timestamp = int(datetime.now(timezone.utc).timestamp())
    response_data = {
        "lock_state": lock_state,
        "timestamp": timestamp,
    }

    return {
        "data": response_data
    }


if __name__ == "__main__":
    uvicorn.run("lock_vuln:app", host="127.0.0.1", port=8001)