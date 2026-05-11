"""Lark (International) OAuth service."""
import httpx
from typing import Optional
from ..config import settings


class LarkAuthService:
    """Handle Lark OAuth2.0 authentication flow."""

    BASE_URL = "https://open.larksuite.com/open-apis"

    def __init__(self):
        self.app_id = settings.LARK_APP_ID
        self.app_secret = settings.LARK_APP_SECRET
        self.redirect_uri = settings.LARK_REDIRECT_URI

    def get_login_url(self, state: str = "") -> str:
        """Generate Lark OAuth login URL."""
        return (
            f"https://open.larksuite.com/open-apis/authen/v1/authorize"
            f"?app_id={self.app_id}"
            f"&redirect_uri={self.redirect_uri}"
            f"&response_type=code"
            f"&state={state}"
        )

    async def get_app_access_token(self) -> str:
        """Get app access token from Lark."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/auth/v3/app_access_token/internal",
                json={
                    "app_id": self.app_id,
                    "app_secret": self.app_secret,
                },
            )
            data = resp.json()
            if data.get("code") != 0:
                raise Exception(f"Failed to get app access token: {data.get('msg')}")
            return data["app_access_token"]

    async def get_user_access_token(self, code: str) -> dict:
        """Exchange authorization code for user access token."""
        app_token = await self.get_app_access_token()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/authen/v1/oidc/access_token",
                headers={"Authorization": f"Bearer {app_token}"},
                json={
                    "grant_type": "authorization_code",
                    "code": code,
                },
            )
            data = resp.json()
            if data.get("code") != 0:
                raise Exception(f"Failed to get user token: {data.get('msg')}")
            return data["data"]

    async def get_user_info(self, user_access_token: str) -> dict:
        """Get user info from Lark using user access token."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/authen/v1/user_info",
                headers={"Authorization": f"Bearer {user_access_token}"},
            )
            data = resp.json()
            if data.get("code") != 0:
                raise Exception(f"Failed to get user info: {data.get('msg')}")
            return data["data"]


lark_auth_service = LarkAuthService()
