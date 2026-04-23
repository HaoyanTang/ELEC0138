from datetime import datetime, timedelta, timezone
from fastapi import Depends, FastAPI, HTTPException, status, Header
from pydantic import BaseModel
import uvicorn
import hmac
import hashlib
import json
import os

PAIRING_CODE = "88888888"
LOCK_ID = 1
SECRET_KEY = b"ELEC0138"
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

def create_hmac_signature(data: dict) -> str:
    message = json.dumps(
        data,
        separators=(",", ":"),
        sort_keys=True
    ).encode()
    return hmac.new(SECRET_KEY, message, hashlib.sha256).hexdigest()

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
    signature: str = Header(..., alias="signature"),
):
    request = {
        "lock_id": lock.lock_id,
        "action": lock.action,
        "password": lock.password,
        "timestamp": lock.timestamp}
    expected_signature = create_hmac_signature(request)
    authenticate = hmac.compare_digest(signature, expected_signature)
    #authentication check
    if not authenticate:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized Message",)
    if str(LOCK_ID) != str(lock.lock_id):
        raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Lock ID mismatch",)
    now = int(datetime.now(timezone.utc).timestamp())
    if abs(now - lock.timestamp) > 60:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Request expired",
        )
    if lock.password != PAIRING_CODE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pairing code mismatch",
        )

    #form a response and use HMAC
    lock_state = load_lock_state()["status"]
    timestamp = int(datetime.now(timezone.utc).timestamp())
    response_data = {
        "lock_id": LOCK_ID,
        "status": "success",
        "action": lock.action,
        "lock_state": lock_state,
        "timestamp": timestamp,
    }
    response_signature = create_hmac_signature(response_data)
    return {
    "data": response_data,
    "signature": response_signature
    }

@app.post("/lock/toggle")
async def toggle_lock(
    lock: ToggleLock,
    signature: str = Header(..., alias="signature"),
):
    request = {
        "lock_id": lock.lock_id,
        "timestamp": lock.timestamp,
    }
    expected_signature = create_hmac_signature(request)
    authenticate = hmac.compare_digest(signature, expected_signature)
    if not authenticate:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized Message",
        )
    now = int(datetime.now(timezone.utc).timestamp())
    if abs(now - lock.timestamp) > 60:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Request expired",
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
    response_signature = create_hmac_signature(response_data)
    return {
    "data": response_data,
    "signature": response_signature
    }

if __name__ == "__main__":
    uvicorn.run(
        "lock:app",
        host="127.0.0.1",
        port=8001,
        ssl_keyfile="../key.pem",
        ssl_certfile="../cert.pem"
    )