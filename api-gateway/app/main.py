from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api-gateway")

app = FastAPI(
    title="Sistema Nacional de Learning Analytics - API Gateway",
    description="API Gateway - Microservicios de Prediccion de Riesgo Academico",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVICE_MAP = {
    "/api/events": os.getenv("EVENT_SERVICE_URL", "http://event-service:8001"),
    "/api/analytics": os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service:8002"),
    "/api/alerts": os.getenv("ALERT_SERVICE_URL", "http://alert-service:8003"),
    "/api/dashboard": os.getenv("DASHBOARD_SERVICE_URL", "http://dashboard-service:8004"),
    "/api/institutions": os.getenv("DASHBOARD_SERVICE_URL", "http://dashboard-service:8004"),
    "/api/reports": os.getenv("DASHBOARD_SERVICE_URL", "http://dashboard-service:8004"),
}

@app.get("/")
async def root():
    return {
        "message": "Sistema Nacional de Learning Analytics - API Gateway",
        "version": "2.0.0",
        "services": {k: v for k, v in SERVICE_MAP.items()},
    }

@app.get("/health")
async def health():
    return {"service": "api-gateway", "status": "ok"}

@app.get("/health/all")
async def health_all():
    results = {}
    async with httpx.AsyncClient(timeout=3) as client:
        for prefix, url in SERVICE_MAP.items():
            try:
                resp = await client.get(f"{url}/health")
                results[prefix] = resp.json()
            except Exception as e:
                results[prefix] = {"status": "unreachable", "error": str(e)}
    return results

@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(request: Request, path: str):
    full_path = f"/api/{path}"
    query = str(request.query_params)
    if query:
        full_path = f"{full_path}?{query}"

    service_url = _match_service(full_path)
    if not service_url:
        return JSONResponse(
            status_code=404,
            content={"error": f"No service found for path: {full_path}", "available": list(SERVICE_MAP.keys())},
        )

    target_url = f"{service_url}{full_path}"
    logger.info(f"Proxying {request.method} {full_path} -> {target_url}")

    body = await request.body()
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body if body else None,
            )
            return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except httpx.ConnectError:
        logger.error(f"Service unreachable: {service_url}")
        return JSONResponse(
            status_code=503,
            content={"error": f"Service unavailable: {service_url}", "path": full_path},
        )
    except Exception as e:
        logger.error(f"Proxy error: {e}")
        return JSONResponse(status_code=502, content={"error": str(e), "path": full_path})

def _match_service(path: str) -> str:
    for prefix in sorted(SERVICE_MAP.keys(), key=len, reverse=True):
        if path.startswith(prefix):
            return SERVICE_MAP[prefix]
    return None
