"""
PromptShield Gateway — Main Application
Campus LLM Privacy & Injection Defender
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from config import settings
from routes import proxy, dashboard, settings as settings_routes

# ── Rate Limiter ───────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ── FastAPI App ────────────────────────────────────────────────────────
app = FastAPI(
    title="PromptShield Gateway",
    description=(
        "Campus LLM Privacy & Injection Defender - "
        "Scrubs PII and detects prompt injection attacks before "
        "forwarding requests to AI models. Built to protect "
        "institutional data and prevent AI-powered threats."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ─────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ─────────────────────────────────────────────────────────────
app.include_router(proxy.router)
app.include_router(dashboard.router)
app.include_router(settings_routes.router)


# ── Root ───────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "service": "PromptShield Gateway",
        "version": "1.0.0",
        "status": "operational",
        "description": "Campus LLM Privacy & Injection Defender",
        "endpoints": {
            "chat": "POST /api/v1/chat - Proxy chat with PII scrubbing",
            "scan": "POST /api/v1/scan - Scan text for threats",
            "stats": "GET /api/v1/stats - Dashboard statistics",
            "threats": "GET /api/v1/threats - Recent threat log",
            "health": "GET /api/v1/health - System health",
            "docs": "GET /docs - Interactive API docs",
        },
    }

