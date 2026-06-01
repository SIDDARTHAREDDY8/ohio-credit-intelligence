"""FastAPI application for the Ohio Credit Intelligence scoring service.

Loads the champion model at startup and exposes scoring, explanation,
decision-history, and monitoring endpoints. All decisions are persisted to
public.decisions.
"""

import logging
import time
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.routers import decisions, monitoring, scoring
from api.security import limiter
from api.services.model_loader import model_service

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        model_service.load()
        print(f"Champion model loaded (version {model_service.model_version})")
    except Exception as e:  # keep the API up so /health can report the failure
        print(f"WARNING: model failed to load at startup: {e}")
    yield


app = FastAPI(
    title="Ohio Credit Intelligence API",
    description="LightGBM credit-risk scoring with SHAP explanations and "
    "ECOA-compliant adverse action notices.",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiting (slowapi): register the limiter and its 429 handler.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scoring.router)
app.include_router(decisions.router)
app.include_router(monitoring.router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {
        "status": "ok",
        "model_loaded": model_service.is_loaded,
        "model_version": model_service.model_version,
        "uptime_seconds": round(time.time() - START_TIME, 1),
    }
