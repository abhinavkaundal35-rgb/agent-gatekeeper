"""Agent Gatekeeper - Main FastAPI Application."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import PROJECT_NAME, BUSINESS_CATEGORY, VERSION
from src.core.database import init_db
from src.iam.router import router as iam_router
from src.store.router import router as store_router
from src.approvals.router import router as approvals_router
from src.audit.router import router as audit_router
from src.gatekeeper.router import router as gatekeeper_router

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

@app.get("/", tags=["System"])
def root():
    return {
        "system": PROJECT_NAME,
        "business_category": BUSINESS_CATEGORY,
        "reference_company": "Amazon India",
        "version": VERSION,
        "status": "OPERATIONAL",
        "docs_url": "/docs",
        "supported_verdicts": ["ALLOW", "ASK CUSTOMER", "BLOCK"]
    }

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
