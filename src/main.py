"""
main.py — Application entry point.

Initializes the FastAPI app, loads the dataset on startup via
lifespan events, registers API routes, and configures middleware
(CORS, error handling, rate limiting, structured logging).
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from collections import defaultdict

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from src.config import settings
from src.data.loader import load_dataset_from_hf
from src.data.preprocessor import build_indices, preprocess
from src.api.routes import router


# ═══════════════════════════════════════════════════════════════════════
# Logging Configuration
# ═══════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.DEBUG if settings.APP_DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Rate Limiter (simple in-memory, per-IP)
# ═══════════════════════════════════════════════════════════════════════

# Configuration
RATE_LIMIT_REQUESTS = 10    # max requests per window
RATE_LIMIT_WINDOW = 60      # window size in seconds

# Storage: IP → list of request timestamps
_rate_limit_store: dict[str, list[float]] = defaultdict(list)


def _is_rate_limited(client_ip: str) -> bool:
    """
    Check whether the given IP has exceeded the rate limit.

    Uses a sliding window: only timestamps within the last
    RATE_LIMIT_WINDOW seconds are counted.
    """
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW

    # Prune old timestamps
    timestamps = _rate_limit_store[client_ip]
    _rate_limit_store[client_ip] = [ts for ts in timestamps if ts > window_start]

    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_REQUESTS:
        return True

    _rate_limit_store[client_ip].append(now)
    return False


# ═══════════════════════════════════════════════════════════════════════
# Lifespan — Dataset Loading on Startup
# ═══════════════════════════════════════════════════════════════════════


async def load_dataset_in_background(app: FastAPI):
    """
    Asynchronously loads and preprocesses the Zomato dataset in the background
    to allow the main server application process to start instantly and answer health checks.
    """
    try:
        logger.info("Background: Loading dataset from Hugging Face…")
        raw_df = load_dataset_from_hf(dataset_id=settings.DATASET_ID)

        logger.info("Background: Preprocessing dataset…")
        clean_df = preprocess(raw_df)

        logger.info("Background: Building lookup indices…")
        indices = build_indices(clean_df)

        # Store in app state for route handlers
        app.state.df = clean_df
        app.state.indices = indices

        logger.info(
            "✅ Background: Dataset ready: %d restaurants, %d locations, %d cuisine types.",
            len(clean_df),
            len(indices.get("locations", [])),
            len(indices.get("cuisines", [])),
        )
    except Exception as exc:
        logger.error("❌ Background: Failed to load dataset: %s", exc, exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Starts dataset load task in the background and releases the startup sequence immediately.
    """
    logger.info("🚀 Starting AI Restaurant Recommendation Service…")

    # Initialise app state
    app.state.df = None
    app.state.indices = None

    # Spawn background task to prevent blocking Uvicorn port binding and health check pings
    asyncio.create_task(load_dataset_in_background(app))

    yield

    # Shutdown cleanup
    logger.info("Shutting down… Cleaning up resources.")
    app.state.df = None
    app.state.indices = None


# ═══════════════════════════════════════════════════════════════════════
# FastAPI App Initialisation
# ═══════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="AI Restaurant Recommendation API",
    description=(
        "An AI-powered restaurant recommendation service that uses the "
        "Zomato dataset and Groq LLM to provide personalised, explainable "
        "restaurant recommendations."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ── CORS Middleware ───────────────────────────────────────────────────
# Allow all origins for local development.
# In production, restrict this to your frontend domain(s).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════
# Error Handling Middleware
# ═══════════════════════════════════════════════════════════════════════


@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    """
    Global error handler and rate limiter.

    - Applies rate limiting on POST /recommend
    - Catches unhandled exceptions and returns sanitised 500 responses
    - Adds response timing header
    """
    start_time = time.time()

    # ── Rate limiting (only on /recommend) ────────────────────────────
    if request.url.path == "/recommend" and request.method == "POST":
        client_ip = request.client.host if request.client else "unknown"
        if _is_rate_limited(client_ip):
            logger.warning("Rate limit exceeded for IP: %s", client_ip)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": {
                        "message": (
                            "Rate limit exceeded. "
                            f"Maximum {RATE_LIMIT_REQUESTS} requests "
                            f"per {RATE_LIMIT_WINDOW} seconds."
                        ),
                        "retry_after_seconds": RATE_LIMIT_WINDOW,
                    }
                },
            )

    # ── Process the request ───────────────────────────────────────────
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error(
            "Unhandled exception on %s %s: %s",
            request.method,
            request.url.path,
            exc,
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An unexpected error occurred. Please try again later.",
            },
        )

    # ── Add timing header ─────────────────────────────────────────────
    elapsed_ms = (time.time() - start_time) * 1000
    response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"

    return response


# ═══════════════════════════════════════════════════════════════════════
# Register Routes
# ═══════════════════════════════════════════════════════════════════════

app.include_router(router)

# Serve static files for the frontend
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_dir = os.path.join(workspace_dir, "frontend")

if os.path.exists(frontend_dir):
    css_dir = os.path.join(frontend_dir, "css")
    js_dir = os.path.join(frontend_dir, "js")
    
    if os.path.exists(css_dir):
        app.mount("/css", StaticFiles(directory=css_dir), name="css")
    if os.path.exists(js_dir):
        app.mount("/js", StaticFiles(directory=js_dir), name="js")
    
    assets_dir = os.path.join(frontend_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

@app.get("/")
async def serve_index():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(
        status_code=404,
        content={"message": "Welcome to AI Restaurant Recommendation API. Frontend index.html not found."}
    )


# ═══════════════════════════════════════════════════════════════════════
# Direct Execution
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
        log_level="debug" if settings.APP_DEBUG else "info",
    )
