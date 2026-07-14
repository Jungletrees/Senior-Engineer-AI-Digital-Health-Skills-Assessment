from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.config import router as config_router
from app.core.errors import AppError, app_error_handler
from app.home.routes import router as home_router
from app.documents.routes import router as documents_router
from app.security.guardrails import InputValidationMiddleware, SecurityHeadersMiddleware
from app.scheduling.cache_scheduler import (
    start_cache_hygiene_scheduler,
    stop_cache_hygiene_scheduler,
)
from app.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache_scheduler_task = start_cache_hygiene_scheduler()
    try:
        yield
    finally:
        await stop_cache_hygiene_scheduler(cache_scheduler_task)


app = FastAPI(lifespan=lifespan)
app.add_exception_handler(AppError, app_error_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(InputValidationMiddleware)

app.include_router(home_router)
app.include_router(auth_router)
app.include_router(config_router)
app.include_router(documents_router)
app.include_router(chat_router)
