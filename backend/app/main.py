import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import admin, auth
from app.api.routers import parser as parser_router
from app.api.routers import anonymize as anonymize_router
from app.api.routers import ats as ats_router
from app.api.routers import jobs as jobs_router
from app.api.routers import pipeline as pipeline_router
from app.api.routers import reports as reports_router
from app.api.routers import ai as ai_router
from app.core.config import get_settings
from app.core.database import init_db

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(title=settings.app_name, version="1.0.0")

allowed_origins = list(
    dict.fromkeys(
        [
            settings.frontend_url,
            f"https://{settings.frontend_hostname}" if settings.frontend_hostname else "",
            # Production domains
            "https://www.innotechninjas.com",
            "https://innotechninjas.com",
            # Local development
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:3002",
            "http://localhost:3003",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:3002",
            "http://127.0.0.1:3003",
            # Extra origins from environment (comma-separated)
            *[o.strip() for o in settings.extra_cors_origins.split(",") if o.strip()],
        ]
    )
)
allowed_origins = [origin for origin in allowed_origins if origin]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(admin.router, prefix=settings.api_v1_prefix)
app.include_router(parser_router.router, prefix=settings.api_v1_prefix)
app.include_router(anonymize_router.router, prefix=settings.api_v1_prefix)
app.include_router(jobs_router.router, prefix=settings.api_v1_prefix)
app.include_router(ats_router.router, prefix=settings.api_v1_prefix)
app.include_router(pipeline_router.router, prefix=settings.api_v1_prefix)
app.include_router(reports_router.router, prefix=settings.api_v1_prefix)
app.include_router(ai_router.router, prefix=settings.api_v2_prefix)

init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
