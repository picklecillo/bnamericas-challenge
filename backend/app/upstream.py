"""Thin client for the upstream records API. Turns its HTTP habits into exceptions."""

import httpx


class UpstreamError(Exception):
    """The upstream failed or could not be reached."""


class UpstreamNotFound(UpstreamError):
    pass


class UpstreamTimeout(UpstreamError):
    """The upstream answered 504. The write may or may not have landed."""


class UpstreamClient:
    def __init__(self, base_url: str, api_key: str, transport: httpx.AsyncBaseTransport | None = None):
        # Slow GETs take ~2s upstream; 5s leaves room without hanging the browser.
        self._http = httpx.AsyncClient(
            base_url=base_url, headers={"X-Api-Key": api_key}, timeout=5.0, transport=transport
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def list_projects(self) -> list[dict]:
        return await self._request("GET", "/projects")

    async def get_project(self, project_id: str) -> dict:
        return await self._request("GET", f"/projects/{project_id}")

    async def put_project(self, project_id: str, body: dict) -> dict:
        return await self._request("PUT", f"/projects/{project_id}", json=body)

    async def _request(self, method: str, path: str, **kwargs):
        try:
            response = await self._http.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise UpstreamTimeout(str(exc)) from exc
        except httpx.HTTPError as exc:
            raise UpstreamError(str(exc)) from exc
        if response.status_code == 404:
            raise UpstreamNotFound(path)
        if response.status_code == 504:
            raise UpstreamTimeout(path)
        if response.is_error:
            raise UpstreamError(f"{method} {path} -> {response.status_code}")
        return response.json()
