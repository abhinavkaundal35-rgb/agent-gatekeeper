"""Agent Gatekeeper - Main FastAPI Application."""
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import PROJECT_NAME, BUSINESS_CATEGORY, VERSION
from src.core.database import init_db
from src.iam.router import router as iam_router
from src.store.router import router as store_router
from src.approvals.router import router as approvals_router
from src.audit.router import router as audit_router
from src.gatekeeper.router import router as gatekeeper_router

UI_HTML_PATH = Path(__file__).resolve().parent / "ui" / "dashboard.html"
STORE_HTML_PATH = Path(__file__).resolve().parent / "ui" / "client_storefront.html"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schemas on startup
    init_db()
    yield

app = FastAPI(
    title=PROJECT_NAME,
    description=f"Security Gatekeeper for Customer AI Agents in {BUSINESS_CATEGORY}. Evaluates requests to ALLOW, ASK CUSTOMER, or BLOCK.",
    version=VERSION,
    lifespan=lifespan
)

# Enable CORS for interactive web consoles
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount modular routers
app.include_router(gatekeeper_router)
app.include_router(iam_router)
app.include_router(store_router)
app.include_router(approvals_router)
app.include_router(audit_router)

@app.get("/", response_class=HTMLResponse, tags=["Web UI"])
def web_dashboard():
    """Serves the interactive Agent Gatekeeper Security & Governance Portal."""
    if UI_HTML_PATH.exists():
        with open(UI_HTML_PATH, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h2>Dashboard HTML not found.</h2>")

@app.get("/store", response_class=HTMLResponse, tags=["Client Storefront"])
@app.get("/shop", response_class=HTMLResponse, tags=["Client Storefront"])
def client_storefront():
    """Serves the dedicated Amazon India Client Storefront for live customer shopping & AI checkout."""
    if STORE_HTML_PATH.exists():
        with open(STORE_HTML_PATH, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h2>Storefront HTML not found.</h2>")

@app.get("/api", tags=["System"])
def api_root():
    return {
        "system": PROJECT_NAME,
        "business_category": BUSINESS_CATEGORY,
        "reference_company": "Amazon India",
        "version": VERSION,
        "status": "OPERATIONAL",
        "docs_url": "/docs",
        "gatekeeper_portal_url": "/",
        "client_storefront_url": "/store",
        "supported_verdicts": ["ALLOW", "ASK CUSTOMER", "BLOCK"]
    }

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
