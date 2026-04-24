from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel
from database import engine, SessionLocal
from models import Base, UserTable, LockTable, UserLockTable
from sqlalchemy.orm import Session
import jwt
import requests
import uvicorn
import hmac, hashlib
import json

#set up jwt(this is for generating token)
SECRET_KEY = "687f5fdec07fbffd228e5f40a705f162457d6abf74d91c432a66aff9a7346ef2"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10

#key for HMAC
SECRET_KEY_LOCK = b"ELEC0138"

#create database
Base.metadata.create_all(bind=engine)

#define class used for API input/output
class LockUpdate(BaseModel):
    lock_state: str

class PairRequest(BaseModel):
    lock_id: int
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

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
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
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

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def create_hmac_signature(data: dict) -> str:
    message = json.dumps(
        data,
        separators=(",", ":"),
        sort_keys=True
    ).encode()
    return hmac.new(SECRET_KEY_LOCK, message, hashlib.sha256).hexdigest()

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

@app.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)]
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

@app.post("/lock/pairlock")
async def pair_lock(
    request: PairRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_active_user)]
    ):
    timestamp = int(datetime.now(timezone.utc).timestamp())
    pair_request = {
        "lock_id": request.lock_id,
        "action": "pairing",
        "password": request.password,
        "timestamp": timestamp,
    }
    signature = create_hmac_signature(pair_request)
    response = requests.post(headers={"signature": signature}, json=pair_request, url=f"https://127.0.0.1:8001/lock/pair", verify = False)
    try:
        response.raise_for_status()
    except requests.HTTPError:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Lock error: {response.text}"
        )

    response_data = response.json()["data"]
    response_signature = response.json()["signature"]
    expected_signature = create_hmac_signature(response_data)
    authenticate = hmac.compare_digest(response_signature, expected_signature)
    #authentication check
    if not authenticate:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized Message",)
    lock_id = response_data["lock_id"]
    lock_state = response_data["lock_state"]
    user_id = db.query(UserTable).filter(UserTable.username == user.username).first().id

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
            status_code=status.HTTP_400_BAD_REQUEST,
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
    return{
        "message": "Pair successful",
        "user_id": user_id,
        "lock_id": lock_id,
        "role": role}

@app.post("/lock/toggle/{lock_id}")
async def control_lock(
    lock_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_active_user)]
):
    timestamp = int(datetime.now(timezone.utc).timestamp())
    toggle_request = {
        "lock_id": lock_id,
        "timestamp": timestamp,
    }
    signature = create_hmac_signature(toggle_request)
    response = requests.post(headers={"signature": signature}, json=toggle_request, url=f"https://127.0.0.1:8001/lock/toggle", verify=False)
    try:
        response.raise_for_status()
    except requests.HTTPError:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Lock error: {response.text}"
        )

    response_data = response.json()["data"]
    response_signature = response.json()["signature"]
    expected_signature = create_hmac_signature(response_data)
    authenticate = hmac.compare_digest(response_signature, expected_signature)
    #authentication check
    if not authenticate:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized Message",)
    lock_state = response_data["lock_state"]
    timestamp = response_data["timestamp"]
    db.query(LockTable).filter(LockTable.lock_id == lock_id).update({"status": lock_state})
    db.commit()
    return{
        "message": "Toggle successful",
    }

@app.get("/locks/me")
async def my_lock(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_active_user)]
):
    me = db.query(UserTable).filter(UserTable.username == user.username).first()
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

@app.get("/users/all")
async def get_all_users(db: Annotated[Session, Depends(get_db)]):
    users = db.query(UserTable).all()
    return users

if __name__ == "__main__":
    uvicorn.run(
        "backend:app",
        host="127.0.0.1",
        port=8000,
        ssl_keyfile="../secured/key.pem",
        ssl_certfile="../secured/cert.pem"
    )
