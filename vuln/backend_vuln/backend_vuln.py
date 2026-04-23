from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import engine, SessionLocal
from models import Base, UserTable, LockTable, UserLockTable

from pwdlib import PasswordHash
import requests
import uvicorn


#create database
Base.metadata.create_all(bind=engine)

#define class used for API input/output
class LockUpdate(BaseModel):
    lock_state: str

class PairRequest(BaseModel):
    username: str
    lock_id: int
    password: str

class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class User(BaseModel):
    username: str
    email: str | None = None
    disabled: bool | None = None

class UserInDB(User):
    hashed_password: str


#set dummy hash, if user not found, compair with dummy hash
password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("dummypassword")

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)

def get_password_hash(password):
    return password_hash.hash(password)

def get_user(db, username: str):
    db_user = db.query(UserTable).filter(UserTable.username == username).first()
    if db_user:
        return UserInDB(
            username=db_user.username,
            email=db_user.email,
            disabled=db_user.disabled,
            hashed_password=db_user.hashed_password,
        )
    return None

def authenticate_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user:
        verify_password(password, DUMMY_HASH)
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


@app.post("/register")
async def register(
    user: UserRegister,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    existing_user = db.query(UserTable).filter(UserTable.username == user.username).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )

    new_user = UserTable(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password),
        disabled=False,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return User(
        username=new_user.username,
        email=new_user.email,
        disabled=new_user.disabled,
    )


@app.post("/login")
async def login(
    user: UserRegister,
    db: Annotated[Session, Depends(get_db)]
):
    authenticated_user = authenticate_user(db, user.username, user.password)
    if not authenticated_user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
        )
    return {
        "message": "Login successful",
        "username": authenticated_user.username
    }


@app.post("/lock/pairlock")
async def pair_lock(
    request: PairRequest,
    db: Annotated[Session, Depends(get_db)],
):
    timestamp = int(datetime.now(timezone.utc).timestamp())
    pair_request = {
        "lock_id": request.lock_id,
        "action": "pairing",
        "password": request.password,
        "timestamp": timestamp,
    }

    response = requests.post(
        json=pair_request,
        url="http://127.0.0.1:8001/lock/pair",
        timeout=5
    )

    try:
        response.raise_for_status()
    except requests.HTTPError:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Lock error: {response.text}"
        )

    response_data = response.json()["data"]

    lock_id = response_data["lock_id"]
    lock_state = response_data["lock_state"]

    db_user = db.query(UserTable).filter(UserTable.username == request.username).first()
    if db_user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    user_id = db_user.id

    lock = db.query(LockTable).filter(LockTable.lock_id == lock_id).first()
    if lock is not None:
        existing_relation = (
            db.query(UserLockTable)
            .filter(
                UserLockTable.user_id == user_id,
                UserLockTable.lock_id == lock_id
            )
            .first()
        )
        if existing_relation is not None:
            raise HTTPException(
                status_code=400,
                detail="User already linked to this lock"
            )
        role = "family"
    else:
        new_lock = LockTable(
            lock_id=lock_id,
            status=lock_state
        )
        db.add(new_lock)
        db.commit()
        db.refresh(new_lock)
        role = "admin"

    new_relation = UserLockTable(
        user_id=user_id,
        lock_id=lock_id,
        role=role,
    )
    db.add(new_relation)
    db.commit()
    db.refresh(new_relation)

    return {
        "message": "Pair successful",
        "user_id": user_id,
        "lock_id": lock_id,
        "role": role
    }


@app.post("/lock/toggle/{lock_id}")
async def control_lock(
    lock_id: int,
    username: str,
    db: Annotated[Session, Depends(get_db)],
):
    db_user = db.query(UserTable).filter(UserTable.username == username).first()
    if db_user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    timestamp = int(datetime.now(timezone.utc).timestamp())
    toggle_request = {
        "lock_id": lock_id,
        "timestamp": timestamp,
    }

    response = requests.post(
        json=toggle_request,
        url="http://127.0.0.1:8001/lock/toggle",
        timeout=5
    )

    try:
        response.raise_for_status()
    except requests.HTTPError:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Lock error: {response.text}"
        )

    response_data = response.json()["data"]
    lock_state = response_data["lock_state"]

    lock = db.query(LockTable).filter(LockTable.lock_id == lock_id).first()
    if lock is None:
        new_lock = LockTable(
            lock_id=lock_id,
            status=lock_state
        )
        db.add(new_lock)
    else:
        lock.status = lock_state

    db.commit()

    return {
        "message": "Toggle successful",
        "username": username,
        "lock_id": lock_id,
        "lock_state": lock_state
    }


@app.get("/locks/me/{username}")
async def my_lock(
    username: str,
    db: Annotated[Session, Depends(get_db)],
):
    me = db.query(UserTable).filter(UserTable.username == username).first()
    if me is None:
        raise HTTPException(status_code=404, detail="User not found")

    locks = [i.lock for i in me.user_lock]
    return [
        {
            "lock_id": i.lock_id,
            "status": i.status
        }
        for i in locks
    ]


@app.delete("/users/{username}")
async def delete_user(username: str, db: Annotated[Session, Depends(get_db)]):
    user = db.query(UserTable).filter(UserTable.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": f"{username} deleted"}


@app.get("/users/all")
async def get_all_users(db: Annotated[Session, Depends(get_db)]):
    users = db.query(UserTable).all()
    return users


if __name__ == "__main__":
    uvicorn.run("backend_vuln:app", host="127.0.0.1", port=8000)