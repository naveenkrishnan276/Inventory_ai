import os

from fastapi import Header, HTTPException, status


API_TOKEN = os.getenv("API_TOKEN", "dev-token")


def verify_api_token(x_api_token: str | None = Header(default=None)):
    if x_api_token != API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token",
        )
