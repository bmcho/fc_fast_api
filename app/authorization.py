# from fastapi import Depends, FastAPI
# from fastapi.security import HTTPBasic, HTTPBasicCredentials

# app = FastAPI()
# security = HTTPBasic()


# @app.get("/users/me")
# def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
#     return {"username": credentials.username, "password": credentials.password}


# OAuth2
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordRequestForm
from jose import jwt
from jose.exceptions import ExpiredSignatureError
from pydantic import BaseModel

app = FastAPI()
security = HTTPBearer()

ALGORITHM = "HS256"
# openssl rand -hex 32
SECRET_KEY = "1d425ed25afc72d7d2007a21ee49e5b2804d25344c3e43c1d4058ec7b076fa04"
fake_user_db = {
    "fastcampus": {
        "id": 1,
        "username": "fastcampus",
        "email": "fastcampus@fastcampus.com",
        "password": "$2b$12$kEsp4W6Vrm57c24ez4H1R.rdzYrXipAuSUZR.hxbqtYpjPLWbYtwS",
    }
}


class User(BaseModel):
    id: int
    username: str
    email: str


class UserPayload(User):
    exp: datetime


async def create_access_token(data: dict, exp: Optional[timedelta] = None):
    expire = datetime.utcnow() + (exp or timedelta(minutes=30))
    user_info = UserPayload(**data, exp=expire)

    return jwt.encode(user_info.dict(), SECRET_KEY, algorithm=ALGORITHM)


async def get_user(cred: HTTPAuthorizationCredentials = Depends(security)):
    token = cred.credentials
    try:
        decoded_data = jwt.decode(token, SECRET_KEY, ALGORITHM)
    except ExpiredSignatureError:
        raise HTTPException(401, "Expired")
    user_info = User(**decoded_data)

    return fake_user_db[user_info.username]


@app.post("/login")
async def issue_token(data: OAuth2PasswordRequestForm = Depends()):
    user = fake_user_db[data.username]

    if bcrypt.checkpw(data.password.encode(), user["password"].encode()):
        return await create_access_token(user, exp=timedelta(minutes=30))
    raise HTTPException(401)


@app.get("/users/me", response_model=User)
async def get_current_user(user: dict = Depends(get_user)):
    return user
