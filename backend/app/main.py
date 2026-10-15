import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from redis.asyncio import Redis

from app.locks import LockBusy, LockError, ProjectLocks
from app.models import ProjectDetail, ProjectSummary, SaveRequest
from app.service import SaveConflict, save_edit
from app.upstream import UpstreamClient, UpstreamError, UpstreamNotFound


def create_app(upstream: UpstreamClient | None = None, locks: ProjectLocks | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        client = upstream or UpstreamClient(
            base_url=os.environ.get("UPSTREAM_URL", "http://127.0.0.1:8081"),
            api_key=os.environ.get("UPSTREAM_API_KEY", "local-dev-key"),
        )
        project_locks = locks or ProjectLocks(Redis.from_url(os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")))
        app.state.upstream = client
        app.state.locks = project_locks
        yield
        await client.aclose()
        await project_locks.aclose()

    app = FastAPI(title="Project editor backend", lifespan=lifespan)

    @app.exception_handler(UpstreamNotFound)
    async def not_found(request: Request, exc: UpstreamNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": "Project not found"})

    @app.exception_handler(SaveConflict)
    async def conflict(request: Request, exc: SaveConflict) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "detail": "Someone else changed the same fields. Choose a value for each and save again.",
                "conflicts": [c.model_dump(mode="json") for c in exc.conflicts],
                "current": exc.current.model_dump(mode="json"),
            },
        )

    @app.exception_handler(UpstreamError)
    async def upstream_failed(request: Request, exc: UpstreamError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": "The records service is unavailable. Try again."})

    @app.exception_handler(LockError)
    async def save_not_guarded(request: Request, exc: LockError) -> JSONResponse:
        if isinstance(exc, LockBusy):
            detail = "Someone else is saving this project right now. Try again in a moment."
        else:
            detail = "Saving is unavailable right now. Try again."
        return JSONResponse(status_code=503, content={"detail": detail})

    def upstream_of(request: Request) -> UpstreamClient:
        return request.app.state.upstream

    @app.get("/api/projects")
    async def list_projects(request: Request) -> list[ProjectSummary]:
        projects = await upstream_of(request).list_projects()
        return [ProjectSummary.model_validate(p) for p in projects]

    @app.get("/api/projects/{project_id}")
    async def get_project(project_id: str, request: Request) -> ProjectDetail:
        return ProjectDetail.model_validate(await upstream_of(request).get_project(project_id))

    @app.put("/api/projects/{project_id}")
    async def save_project(project_id: str, body: SaveRequest, request: Request) -> ProjectDetail:
        return await save_edit(upstream_of(request), request.app.state.locks, project_id, body)

    return app


app = create_app()
