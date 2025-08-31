from fastapi import Header, FastAPI, WebSocket, WebSocketDisconnect,  Depends, HTTPException, Security
from contextlib import asynccontextmanager
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
# from conf.config import SECRET_KEY
from typing import Optional, List
security = HTTPBearer()
#
# SECRET_KEY = 'mySecretSigningKey123456789012345678901234567890'
# def decode_jwt(token: str):
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
#         return payload
#     except jwt.PyJWTError:
#         raise HTTPException(status_code=401, detail="Invalid token")
#
# def get_current_user_roles(token: HTTPAuthorizationCredentials = Security(security)):
#     payload = decode_jwt(token.credentials)
#     roles = payload.get("roles", [])
#     if not roles:
#         raise HTTPException(status_code=403, detail="No roles found in token")
#     return roles
#
# def role_checker(required_roles: list):
#     def checker(roles: list = Depends(get_current_user_roles)):
#         if not any(role in roles for role in required_roles):
#             raise HTTPException(status_code=403, detail="Operation not permitted")
#     return checker

def get_user_from_headers(
        x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
        x_user_roles: Optional[str] = Header(None, alias="X-User-Roles")
):
    if not x_user_email:
        raise HTTPException(status_code=401, detail="Authentication required")

    roles = []
    if x_user_roles:
        roles = [role.strip() for role in x_user_roles.split(",")]

    return {"email": x_user_email, "roles": roles}


def role_checker(required_roles: List[str]):
    def checker(user_info: dict = Depends(get_user_from_headers)):
        user_roles = user_info["roles"]
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(status_code=403, detail="Operation not permitted")
        return True

    return checker