import re
from urllib.parse import urlparse, urlunparse
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from app.constent import ALGORITHM, SECRET_KEY
from app.models import Endpoint, LogoutToken, User
from app.params import DELETED
from database import get_db
from sqlalchemy.orm import Session


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request, db: Session = Depends(get_db)):
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if credentials.scheme != "Bearer":
            raise HTTPException(
                status_code=401, detail="Invalid authentication scheme."
            )

        user_data = self.verify_token(credentials.credentials, request, db)

        if user_data is False:
            raise HTTPException(
                status_code=401, detail="Invalid token or expired token."
            )

        return user_data

    def verify_token(self, token: str, request, db):
        try:

            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload["email"]
            if email is None:
                raise HTTPException(
                    status_code=401, detail="Invalid token or expired token."
                )
            data = payload["id"]
            islogout = db.query(LogoutToken).filter(LogoutToken.token == token).first()
            if islogout:
                raise HTTPException(
                    status_code=401, detail="Invalid token or expired token."
                )
            self.has_permissions(data, request, db)
            return payload
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=401, detail="Invalid token or expired token."
            )

    def has_permissions(self, payload, request, db):
        user = (
            db.query(User)
            .filter(
                User.id == payload, User.deleted == DELETED, User.record_status == 1
            )
            .first()
        )

        if user:
            base_path = re.sub(r"/\d+", "", request.url.path)
            access = (
                db.query(Endpoint)
                .filter(
                    Endpoint.url == base_path,
                    Endpoint.default_role_access_id == user.role_id,
                )
                .first()
            )

            if access:
                pass
            else:
                raise HTTPException(status_code=400, detail="Access Denied")
        else:
            raise HTTPException(status_code=401, detail="Invalid User")
