from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from security import verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


async def get_current_user(token: str = Depends(oauth2_scheme)):

    payload = verify_token(token)

    return payload
