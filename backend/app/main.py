import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("daechul")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작 시 금리 갱신 스케줄러 실행."""
    from app.fetchers.scheduler import rate_update_loop

    task = asyncio.create_task(rate_update_loop())
    logger.info("금리 갱신 스케줄러 시작")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("금리 갱신 스케줄러 종료")


app = FastAPI(
    title="daechul-recommend",
    description="대출 추천 시뮬레이터 API",
    version="0.1.0",
    lifespan=lifespan,
)

origins = settings.parsed_cors_origins
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    path = request.url.path
    if path == "/health":
        return await call_next(request)

    start = time.time()
    response = await call_next(request)
    elapsed = (time.time() - start) * 1000

    logger.info(f"{request.method} {path} {response.status_code} {elapsed:.0f}ms")
    return response


app.include_router(router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
