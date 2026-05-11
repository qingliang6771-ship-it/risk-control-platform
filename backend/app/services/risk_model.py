"""Risk model query service."""
import httpx
from typing import Optional
from ..config import settings


class RiskModelService:
    """Service to query various risk control model APIs."""

    def __init__(self):
        self.base_url = settings.RISK_MODEL_BASE_URL
        self.api_key = settings.RISK_MODEL_API_KEY

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def get_risk_score(self, user_id: str) -> dict:
        """Get comprehensive risk score for a user."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/api/v1/risk/score/{user_id}",
                headers=self._get_headers(),
            )
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"Failed to get risk score: {resp.status_code}", "detail": resp.text}

    async def get_fraud_detection(self, user_id: str) -> dict:
        """Get fraud detection model result for a user."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/models/fraud-detection",
                headers=self._get_headers(),
                json={"user_id": user_id},
            )
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"Fraud detection failed: {resp.status_code}", "detail": resp.text}

    async def get_credit_assessment(self, user_id: str) -> dict:
        """Get credit assessment model result for a user."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/models/credit-assessment",
                headers=self._get_headers(),
                json={"user_id": user_id},
            )
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"Credit assessment failed: {resp.status_code}", "detail": resp.text}

    async def get_behavior_analysis(self, user_id: str) -> dict:
        """Get behavior analysis model result for a user."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/models/behavior-analysis",
                headers=self._get_headers(),
                json={"user_id": user_id},
            )
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"Behavior analysis failed: {resp.status_code}", "detail": resp.text}

    async def get_device_fingerprint(self, user_id: str) -> dict:
        """Get device fingerprint risk analysis for a user."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/models/device-fingerprint",
                headers=self._get_headers(),
                json={"user_id": user_id},
            )
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"Device fingerprint failed: {resp.status_code}", "detail": resp.text}

    async def get_all_models_result(self, user_id: str) -> dict:
        """Get results from all risk models for a user."""
        import asyncio
        results = await asyncio.gather(
            self.get_risk_score(user_id),
            self.get_fraud_detection(user_id),
            self.get_credit_assessment(user_id),
            self.get_behavior_analysis(user_id),
            self.get_device_fingerprint(user_id),
            return_exceptions=True,
        )

        return {
            "user_id": user_id,
            "risk_score": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
            "fraud_detection": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
            "credit_assessment": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
            "behavior_analysis": results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])},
            "device_fingerprint": results[4] if not isinstance(results[4], Exception) else {"error": str(results[4])},
        }


risk_model_service = RiskModelService()
