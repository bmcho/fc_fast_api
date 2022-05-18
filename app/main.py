from tempfile import NamedTemporaryFile
from typing import IO, Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

import app.models as models
import app.schemas as schemas
from app.custom_error import SomeError, SomeFastAPIError
from app.database import SessionLocal, engine
from app.dp_injection import ClassParams, PydanticParams

models.Base.metadata.create_all(bind=engine)


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    return {"username": username}


@app.post("/signin")
def signin(
    username: str = Form(...),
    password: str = Form(...),
    file: UploadFile = File(...),
):
    return {"username": username}


"""
Users
"""

users = {1: {"name": "Fast"}, 2: {"name": "Campus"}, 3: {"name": "API"}}


@app.post("/users", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existed_user = db.query(models.User).filter_by(email=user.email).first()

    if existed_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(email=user.email, password=user.password)
    db.add(user)
    db.commit()

    return user


@app.get("/users", response_model=List[schemas.User])
def read_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    if user_id not in users.keys():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"<User: {user_id}> is not exists.",
        )
    return users[user_id]


"""
file
"""


@app.post("/file/size")
def get_filesize(file: bytes = File(...)):
    return {"file_size": len(file)}


@app.post("/file/info")
async def get_file_info(file: UploadFile = File(...)):
    # file_like_obj = file.file
    # contents = await file.read()

    return {
        "content_type": file.content_type,
        "filename": file.filename,
    }


async def save_file(file: IO):
    # s3 업로드라고 생각해 봅시다. delete=True(기본값)이면
    # 현재 함수가 닫히고 파일도 지워집니다.
    # NamedTemporaryFile <- 임시파일
    with NamedTemporaryFile("wb", delete=False) as tempfile:
        tempfile.write(file.read())
        return tempfile.name


@app.post("/file/store")
async def store_file(file: UploadFile = File(...)):
    path = await save_file(file.file)
    return {"filepath": path}


"""
error
"""


@app.get("/error")
async def get_error():
    raise SomeError("Hello", 500)


@app.get("/error2")
async def get_error2():
    raise SomeFastAPIError(500, "Hello")


@app.exception_handler(SomeError)
async def some_error_handler(request: Request, exc: SomeError):
    print(exc)
    return JSONResponse(content={"message": f"error is {exc.name}"}, status_code=exc.code)


"""
di
"""

items = ({"name": "Foo"}, {"name": "Bar"}, {"name": "Baz"})


async def func_params(q: Optional[str] = None, offset: int = 0, limit: int = 100) -> Dict[str, Any]:
    return {"q": q, "offset": offset, "limit": limit}


@app.get("/items/func")
async def get_items_with_func(params: dict = Depends(func_params)):
    response = {}
    if params["q"]:
        response.update({"q": params["q"]})

    result = items[params["offset"] : params["offset"] + params["limit"]]
    response.update({"items": result})

    return response


@app.get("/items/class")
async def get_items_with_class(params: ClassParams = Depends(ClassParams)):
    response = {}
    if params.q:
        response.update({"q": params.q})

    result = items[params.offset : params.offset + params.limit]
    response.update({"items": result})

    return response


@app.get("/items/pydantic")
async def get_items_with_pydantic(params: PydanticParams = Depends()):
    response = {}
    if params.q:
        response.update({"q": params.q})

    result = items[params.offset : params.offset + params.limit]
    response.update({"items": result})

    return response


# DI의 DI
async def get_q(q: Optional[str] = None) -> Optional[str]:
    return q


async def func_params_with_sub(
    q: Optional[str] = Depends(get_q), offset: int = 0, limit: int = 100
) -> Dict[str, Any]:
    return {"q": q, "offset": offset, "limit": limit}


@app.get("/items/func/sub")
async def get_items_with_func_sub(params: dict = Depends(func_params_with_sub)):
    response = {}
    if params["q"]:
        response.update({"q": params["q"]})

    result = items[params["offset"] : params["offset"] + params["limit"]]
    response.update({"items": result})

    return response


# route 데코레이터의 DI
async def verify_token(x_token: str = Header(...)) -> None:
    if len(x_token) < 10:
        raise HTTPException(401, detail="Not authorized")


# dependencies <- list로 줘야한다
@app.get("/items", dependencies=[Depends(verify_token)])
async def get_items():
    return items
