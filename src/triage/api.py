"""Local read-only JSON API. No model calls, HTML rendering, or database writes."""

import os
from typing import Annotated, Literal

from fastapi import FastAPI, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from triage.storage import (
    DatabaseSettings,
    ResultPage,
    ResultQuery,
    StorageUnavailable,
    Store,
    StoredResult,
)


def create_app(store: Store | None = None) -> FastAPI:
    repository = Store(DatabaseSettings.from_env(os.environ)) if store is None else store
    app = FastAPI(title="Wikipedia edit triage results", version="1.0", redoc_url=None)

    @app.middleware("http")
    async def response_headers(request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse({"error": "invalid_request"}, status_code=422)

    @app.exception_handler(StorageUnavailable)
    async def unavailable(request: Request, exc: StorageUnavailable) -> JSONResponse:
        return JSONResponse({"error": "storage_unavailable"}, status_code=503)

    @app.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/health/ready", response_model=None)
    def ready() -> dict[str, str] | JSONResponse:
        if not repository.ready():
            return JSONResponse({"error": "storage_not_ready"}, status_code=503)
        return {"status": "ready"}

    @app.get("/results", response_model=ResultPage)
    def results(query: Annotated[ResultQuery, Query()]) -> ResultPage:
        return repository.list(query)

    @app.get("/results/{wiki}/{revision_id}", response_model=StoredResult)
    def result(
        wiki: Literal["enwiki"],
        revision_id: Annotated[int, Path(gt=0, le=9_007_199_254_740_991)],
        analysis_version: Annotated[str, Query(min_length=1, max_length=512, pattern=r"\S")],
    ) -> StoredResult | JSONResponse:
        stored = repository.get(wiki, revision_id, analysis_version)
        if stored is None:
            return JSONResponse({"error": "not_found"}, status_code=404)
        return stored

    return app
