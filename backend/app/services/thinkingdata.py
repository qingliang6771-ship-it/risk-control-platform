"""ThinkingData (数数) SQL Query Service."""
import httpx
import json
from urllib.parse import urlencode
from typing import Optional
from ..config import settings


class ThinkingDataService:
    """Handle ThinkingData SQL query API calls."""

    def __init__(self):
        self.base_url = settings.TA_API_URL  # e.g. http://ta2:8992
        self.token = settings.TA_API_TOKEN

    async def query_sql(
        self,
        sql: str,
        format: str = "json",
        timeout_seconds: int = 30,
    ) -> dict:
        """
        Execute SQL query via /open/execute-sql endpoint.
        Uses the paged endpoint (min pageSize=1000) which handles special chars properly.
        Returns parsed JSON result with headers and rows.
        """
        params = {
            "token": self.token,
            "format": format,
            "pageSize": 1000,
            "timeoutSeconds": timeout_seconds,
        }
        url = f"{self.base_url}/open/execute-sql?{urlencode(params)}"

        async with httpx.AsyncClient(timeout=timeout_seconds + 10) as client:
            resp = await client.post(
                url,
                data={"sql": sql},
            )

        if resp.status_code != 200:
            raise Exception(f"ThinkingData API error: HTTP {resp.status_code}")

        result = resp.json()
        if result.get("return_code") != 0:
            raise Exception(f"ThinkingData query failed: {result.get('return_message')}")

        data = result.get("data", {})
        headers = data.get("headers", [])
        row_count = data.get("rowCount", 0)
        task_id = data.get("taskId")

        # If there are results, fetch the first page
        rows = []
        if row_count > 0 and task_id:
            rows = await self.get_page_result(task_id, page_id=0)

        return {
            "headers": headers,
            "rows": rows,
            "row_count": len(rows),
            "error": None,
        }

    async def query_sql_paged(
        self,
        sql: str,
        page_size: int = 10000,
        format: str = "json",
        timeout_seconds: int = 60,
    ) -> dict:
        """
        Execute paged SQL query via /open/execute-sql endpoint.
        Returns task info for large result sets.
        """
        params = {
            "token": self.token,
            "format": format,
            "pageSize": page_size,
            "timeoutSeconds": timeout_seconds,
        }
        url = f"{self.base_url}/open/execute-sql?{urlencode(params)}"

        async with httpx.AsyncClient(timeout=timeout_seconds + 10) as client:
            resp = await client.post(
                url,
                content=f"sql={sql}",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if resp.status_code != 200:
            raise Exception(f"ThinkingData API error: HTTP {resp.status_code}")

        result = resp.json()
        if result.get("return_code") != 0:
            raise Exception(f"ThinkingData query failed: {result.get('return_message')}")

        return result.get("data", {})

    async def get_page_result(self, task_id: str, page_id: int = 0) -> list:
        """
        Download paged result via /open/sql-result-page endpoint.
        """
        params = {
            "token": self.token,
            "taskId": task_id,
            "pageId": page_id,
        }
        url = f"{self.base_url}/open/sql-result-page?{urlencode(params)}"

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url)

        if resp.status_code != 200:
            raise Exception(f"ThinkingData API error: HTTP {resp.status_code}")

        lines = resp.text.strip().split("\n")
        rows = []
        for line in lines:
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    rows.append(line)
        return rows

    async def submit_async_sql(self, sql: str, format: str = "json") -> str:
        """
        Submit async SQL query via /open/submit-sql endpoint.
        Returns task_id.
        """
        params = {
            "token": self.token,
            "format": format,
        }
        url = f"{self.base_url}/open/submit-sql?{urlencode(params)}"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                content=f"sql={sql}",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        result = resp.json()
        if result.get("return_code") != 0:
            raise Exception(f"ThinkingData submit failed: {result.get('return_message')}")

        return result["data"]["taskId"]

    async def get_task_status(self, task_id: str) -> dict:
        """
        Check async task status via /open/sql-task-info endpoint.
        """
        params = {
            "token": self.token,
            "taskId": task_id,
        }
        url = f"{self.base_url}/open/sql-task-info?{urlencode(params)}"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)

        result = resp.json()
        if result.get("return_code") != 0:
            raise Exception(f"ThinkingData task info failed: {result.get('return_message')}")

        return result.get("data", {})


ta_service = ThinkingDataService()
