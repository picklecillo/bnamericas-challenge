"""In-memory stand-in for the upstream records API, with its habits made scriptable.

Served through httpx.MockTransport, so tests are deterministic and never touch upstream/.
"""

import asyncio
import copy
import json
from collections.abc import Callable

import httpx

API_KEY = "local-dev-key"
EDITABLE = ("name", "sector", "country", "stage", "key_dates", "linked_companies")


def wide_project(project_id: str = "P-1001", **overrides) -> dict:
    project = {
        "id": project_id,
        "name": "Cerro Talvi Solar Park",
        "sector": "energy",
        "country": "Chile",
        "stage": "feasibility",
        "key_dates": [
            {"label": "Tender launch", "date": "2026-01-10"},
            {"label": "Financial close", "date": "2026-07-29"},
        ],
        "linked_companies": [{"name": "Varelo Energia SA", "role": "owner"}],
        # Read-only fields owned by other systems.
        "internal_code": "IC-123456",
        "capacity": {"value": 120, "unit": "MW"},
        "source_system": "legacy",
    }
    return project | overrides


class FakeUpstream:
    def __init__(self, *projects: dict):
        self.store = {p["id"]: copy.deepcopy(p) for p in projects}
        self.puts: list[dict] = []
        # Each entry decides the next PUT: "ok", "504_landed" or "504_lost".
        self.put_outcomes: list[str] = []
        # Runs just before a PUT is applied: lets a test play a concurrent writer.
        self.before_put: Callable[[], None] | None = None
        self.down = False
        # Seconds every GET of one project waits before answering, so concurrent saves overlap.
        self.get_delay = 0.0

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def write(self, project_id: str, **fields) -> None:
        """Write straight to the store, like another editor or the nightly import."""
        self.store[project_id].update(copy.deepcopy(fields))

    async def handle(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            raise httpx.ConnectError("upstream down", request=request)
        if request.headers.get("X-Api-Key") != API_KEY:
            return httpx.Response(401, json={"detail": "Missing or invalid X-Api-Key"})

        path = request.url.path
        if request.method == "GET" and path == "/projects":
            return httpx.Response(200, json=list(self.store.values()))

        project_id = path.removeprefix("/projects/")
        if project_id not in self.store:
            return httpx.Response(404, json={"detail": f"Project {project_id} not found"})

        if request.method == "GET":
            snapshot = copy.deepcopy(self.store[project_id])
            if self.get_delay:
                await asyncio.sleep(self.get_delay)
            return httpx.Response(200, json=snapshot)

        if request.method == "PUT":
            body = json.loads(request.content)
            self.puts.append(body)
            if self.before_put:
                hook, self.before_put = self.before_put, None
                hook()
            outcome = self.put_outcomes.pop(0) if self.put_outcomes else "ok"
            if outcome != "504_lost":
                self.store[project_id].update({k: body[k] for k in EDITABLE})
            if outcome.startswith("504"):
                return httpx.Response(504, json={"detail": "Gateway timeout"})
            return httpx.Response(200, json=self.store[project_id])

        return httpx.Response(405)
