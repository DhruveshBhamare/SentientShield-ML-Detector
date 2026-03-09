from typing import Dict
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from .config import JWT_SECRET, JWT_ALG, JWT_ISSUER, JWT_AUDIENCE


security = HTTPBearer()


def verify_jwt_token(token: str) -> Dict:
    try:
        options = {"require": ["exp"]}  # require expiration
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALG],
            issuer=JWT_ISSUER if JWT_ISSUER else None,
            audience=JWT_AUDIENCE if JWT_AUDIENCE else None,
            options=options,
        )
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {e}")


async def auth_dependency(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    token = credentials.credentials
    return verify_jwt_token(token)