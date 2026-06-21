import logging
from typing import Any

import httpx

from knowledge_os.config import Settings
from knowledge_os.domain.common import AuthenticationError

logger = logging.getLogger(__name__)


class GoogleIdentityProvider:
    def __init__(self, settings: Settings) -> None:
        self._client_id = settings.google_client_id

    async def verify_id_token(self, id_token: str) -> dict[str, Any]:
        """Verifies the Google ID token either via Google API (network call)

        or mock logic for testing/development.
        """
        # Developer Mock Token support for testing/offline development
        if id_token.startswith("mock-google-token-"):
            email = id_token.replace("mock-google-token-", "").strip().lower()
            if not email or "@" not in email:
                raise AuthenticationError("Invalid mock Google token format", "invalid_mock_token")
            name = email.split("@")[0].title()
            logger.info(f"Mock Google login verified for: {email}")
            return {
                "email": email,
                "email_verified": True,
                "name": name,
                "sub": f"mock-sub-{email}",
            }

        # Real Google Token verification
        url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                if response.status_code != 200:
                    logger.error(
                        f"Google tokeninfo API returned {response.status_code}: {response.text}"
                    )
                    raise AuthenticationError(
                        "Failed to verify token with Google", "invalid_google_token"
                    )
                payload = response.json()
        except httpx.RequestError as exc:
            logger.error(f"Network error contacting Google OAuth API: {exc}")
            raise AuthenticationError(
                "Unable to contact Google verification service", "google_service_error"
            ) from exc

        # Validate standard ID token claims
        iss = payload.get("iss", "")
        if iss not in {"accounts.google.com", "https://accounts.google.com"}:
            raise AuthenticationError("Invalid issuer on Google token", "invalid_google_issuer")

        email_verified = payload.get("email_verified")
        # email_verified can be boolean or the string "true"
        if email_verified not in {True, "true"}:
            raise AuthenticationError("Google email is not verified", "google_email_unverified")

        email = payload.get("email")
        if not email:
            raise AuthenticationError(
                "Google token is missing email address", "google_email_missing"
            )

        # Optional Audience check if client ID is configured
        aud = payload.get("aud", "")
        if self._client_id and aud != self._client_id:
            logger.warning(
                f"Google token audience '{aud}' does not match client_id '{self._client_id}'"
            )
            raise AuthenticationError("Google token audience mismatch", "invalid_google_audience")

        return {
            "email": email.strip().lower(),
            "name": payload.get("name", email.split("@")[0]).strip(),
            "sub": payload.get("sub", ""),
        }
