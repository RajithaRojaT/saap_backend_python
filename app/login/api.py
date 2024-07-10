from fastapi import HTTPException, Request
from fastapi import APIRouter, Depends
from fastapi_sqlalchemy import db
import jwt
from datetime import datetime, timedelta
from google.oauth2 import id_token
from google.auth.transport import requests
from sqlalchemy.orm import Session
from app.constent import ALGORITHM, SECRET_KEY
from app.login.auth import JWTBearer
from app.models import LogoutToken, User
from app.params import DELETED, RECORD_STATUS
from database import get_db
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer
from typing import List

load_dotenv()
# Get the database URL from the environment
google_id = os.getenv("google_id")
auth_route = APIRouter(prefix="/auth")
# Dummy storage for invalid tokens
invalid_tokens: List[str] = []


@auth_route.post("/register")
async def register_user(request: dict, db: Session = Depends(get_db)):
    # Check if user already exists
    idinfo = ""
    try:
        idinfo = id_token.verify_oauth2_token(
            request.get("id_token"),
            requests.Request(),
            google_id,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user or session expired")

    if idinfo["email"] is None and idinfo["sub"] is None:
        raise HTTPException(status_code=401, detail="Invalid user or session expired")

    # Check if user exists
    user = db.query(User).filter_by(email=idinfo["email"]).first()
    if user:
        access_token = create_access_token(user.email, user.id, "refresh")
        return {"token": access_token}

    try:
        user_data = {
            "email": idinfo["email"],
            "external_login_id": idinfo["sub"],
            "name": idinfo["name"],
            "picture_url": idinfo["picture"],
            "authentication_type": idinfo["iss"],
            "created_by": 1,
        }
        user = User(**user_data)
        db.add(user)
        db.commit()
        db.refresh(user)
        db.close()
        access_token = create_access_token(user.email, user.id, "refresh")

        return {"token": access_token, "user_id": user.id}
    except Exception as e:
        db.rollback()
        db.close()
        raise HTTPException(status_code=500, detail=str(e))


@auth_route.post("/login")
async def login(request: dict, db: Session = Depends(get_db)):
    idinfo = ""
    try:
        idinfo = id_token.verify_oauth2_token(
            request.get("id_token"),
            requests.Request(),
            google_id,
        )
    except ValueError:

        raise HTTPException(status_code=401, detail="Invalid user or session expired")

    if idinfo["email"] is None and idinfo["sub"] is None:
        raise HTTPException(status_code=401, detail="Invalid user or session expired")

    # Check if user exists
    user = db.query(User).filter_by(email=idinfo["email"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not registered")

    # Generate access token
    refreh_token = create_access_token(user.email, user.id, "refresh")
    db.close()
    return {"token": refreh_token, "user_id": user.id}


def create_access_token(email: str, user_id: int, type):
    to_encode = {"email": email, "id": user_id}
    if type == "refresh":
        expire = datetime.utcnow() + timedelta(weeks=2)
    else:
        expire = datetime.utcnow() + timedelta(weeks=52)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return encoded_jwt


@auth_route.get("/get_by_user")
def get_subject(
    email: str,
    db: Session = Depends(get_db),
    # user_data: dict = Depends(JWTBearer())
):
    """
    This function retrieves a user by their email address from the database.

    :param email: The `email` parameter in the `get_subject` function is a string type that represents
    the email address of the user you want to retrieve from the database
    :type email: str
    :param db: The `db` parameter in the function `get_subject` is used to provide a database session to
    the function. It is of type `Session` and is obtained using the `Depends` function with the `get_db`
    function as an argument. This parameter allows the function to interact with the
    :type db: Session
    :return: The function `get_subject` is returning the user object that matches the provided email
    address from the database. If the user is not found, it raises an HTTPException with a status code
    of 404 and the detail "Invalid user".
    """
    user = (
        db.query(User)
        .filter(
            User.email == email,
            User.deleted == DELETED,
            User.record_status == RECORD_STATUS,
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Invalid user")
    db.close()
    return user


@auth_route.post("/logout")
async def logout(request: dict, db: Session = Depends(get_db)):
    payload = jwt.decode(request.get("token"), SECRET_KEY, algorithms=[ALGORITHM])
    id = payload["id"]
    user_data = {
        "user_id": id,
        "token": request.get("token"),
        "created_by_id": id,
        "updated_by_id": id,
    }
    invalid_tokens = LogoutToken(**user_data)
    db.add(invalid_tokens)
    db.commit()
    db.refresh(invalid_tokens)
    db.close()
    return {"msg": "Successfully logged out"}
