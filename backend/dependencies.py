from fastapi import Depends, HTTPException, Request
from security import verify_token

async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        # Check authorization header as fallback
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        # Redirect to login logic handled by frontend or return 401
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_token(token)
    return payload


#extraction function



#mapping function



#scoring function


