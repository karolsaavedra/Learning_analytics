"""
Sistema Nacional de Learning Analytics
Main FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import events, analytics, alerts, dashboard, institutions, reports
from app.core.config import settings

app = FastAPI(
    title="Sistema Nacional de Learning Analytics",
    description="API para predicción de riesgo académico en educación tecnológica",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(events.router,       prefix="/api/events",       tags=["Event Service"])
app.include_router(analytics.router,    prefix="/api/analytics",    tags=["Analytics Service"])
app.include_router(alerts.router,       prefix="/api/alerts",       tags=["Alert Service"])
app.include_router(dashboard.router,    prefix="/api/dashboard",    tags=["Dashboard Service"])
app.include_router(institutions.router, prefix="/api/institutions", tags=["Institution Service"])
app.include_router(reports.router,      prefix="/api/reports",      tags=["Report Service"])


@app.get("/")
async def root():
    return JSONResponse({"message": "Sistema Nacional de Learning Analytics API", "version": "1.0.0"})


@app.get("/health")
async def health():
    return {"status": "ok"}
