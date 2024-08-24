from datetime import datetime, timezone, timedelta

import jwt
from passlib.context import CryptContext

from exceptions import VerifyTokenError

ALGORITHM = "HS256"
EXPIRATION_TIME = timedelta(weeks=1)
AUTH_SECRET_KEY = "abcdef"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password):
    return pwd_context.hash(password)


def verify_password(password, password_hash):
    return pwd_context.verify(password, password_hash)


def create_token(data):
    data["exp"] = datetime.now(timezone.utc) + EXPIRATION_TIME
    return jwt.encode(
        data, AUTH_SECRET_KEY, algorithm=ALGORITHM
    )


def verify_token(token):
    try:
        return jwt.decode(
            token, AUTH_SECRET_KEY, algorithms=[ALGORITHM]
        )
    except jwt.PyJWTError:
        raise VerifyTokenError()
