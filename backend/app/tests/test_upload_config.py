from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.config import router
from app.settings import settings


@pytest.mark.asyncio
async def test_upload_limits_endpoint_returns_settings_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "max_pdf_size_mb", 11)
    monkeypatch.setattr(settings, "max_pdf_pages", 22)
    monkeypatch.setattr(settings, "allowed_mime_types", "application/pdf")
    app = FastAPI()
    app.include_router(router)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/config/upload-limits")

    assert response.status_code == 200
    assert response.json() == {
        "max_size_mb": 11,
        "max_pages": 22,
        "allowed_mime_types": ["application/pdf"],
    }
