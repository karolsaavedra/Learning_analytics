from fastapi import FastAPI
import logging
import httpx
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dashboard-service")

app = FastAPI(title="Dashboard Service", version="1.0.0")

ANALYTICS_SERVICE_URL = os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service:8002")
ALERT_SERVICE_URL = os.getenv("ALERT_SERVICE_URL", "http://alert-service:8003")
EVENT_SERVICE_URL = os.getenv("EVENT_SERVICE_URL", "http://event-service:8001")

@app.get("/health")
async def health():
    return {"service": "dashboard-service", "status": "ok"}

@app.get("/api/dashboard/summary")
async def get_dashboard_summary():
    """Aggregator pattern: fetches data from analytics + alert services"""
    logger.info("Aggregating dashboard summary from multiple services")

    stats = None
    alerts_data = None

    async with httpx.AsyncClient(timeout=5) as client:
        try:
            resp = await client.get(f"{ANALYTICS_SERVICE_URL}/api/analytics/stats")
            stats = resp.json()
            logger.info("Fetched stats from analytics-service")
        except Exception as e:
            logger.warning(f"analytics-service unavailable: {e}")

        try:
            resp = await client.get(f"{ALERT_SERVICE_URL}/api/alerts/unread-count")
            alerts_data = resp.json()
            logger.info("Fetched alerts from alert-service")
        except Exception as e:
            logger.warning(f"alert-service unavailable: {e}")

    if stats:
        result = stats
    else:
        result = _mock_stats()

    if alerts_data:
        result["active_alerts"] = alerts_data.get("unread", 0)

    return result

@app.get("/api/institutions")
async def list_institutions():
    return {
        "institutions": [
            {"id": "UNAL", "name": "Universidad Nacional de Colombia", "city": "Bogota", "active": True},
            {"id": "UDEA", "name": "Universidad de Antioquia", "city": "Medellin", "active": True},
            {"id": "UDISTRITAL", "name": "Universidad Distrital", "city": "Bogota", "active": True},
            {"id": "ITBA", "name": "ITBA", "city": "Barranquilla", "active": True},
            {"id": "UNICAUCA", "name": "Universidad del Cauca", "city": "Popayan", "active": True},
        ]
    }

@app.get("/api/institutions/{institution_id}/stats")
async def get_institution_stats(institution_id: str):
    return {
        "institution_id": institution_id,
        "total_students": 2500,
        "students_at_risk": 420,
        "avg_risk_score": 0.31,
        "dropout_rate": 0.18,
        "top_risk_courses": ["Calculo I", "Programacion I", "Algebra"]
    }

@app.get("/api/reports/national")
async def get_national_report():
    from datetime import datetime
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "period": "2026-I",
        "summary": {
            "total_enrolled": 125000,
            "dropout_national": 0.187,
            "high_risk_count": 23400,
            "institutions_reporting": 47,
            "alerts_generated": 8932,
        },
        "by_program": [
            {"program": "Ingenieria de Sistemas", "dropout_rate": 0.22},
            {"program": "IA & Data Science", "dropout_rate": 0.18},
            {"program": "Tecnologia en Programacion", "dropout_rate": 0.31},
        ],
        "recommendations": [
            "Reforzar tutorias en cursos de primer semestre",
            "Implementar mentorias en cursos con tasa de riesgo >25%",
            "Ampliar horas de acceso a laboratorios de computo",
        ]
    }

@app.get("/api/reports/export")
async def export_report():
    return {"status": "Report generation queued", "job_id": "rpt_20260518_001"}

@app.get("/api/dashboard/institutions")
async def get_institutions():
    return {
        "institutions": [
            {"id": "UNAL", "name": "Universidad Nacional", "students": 3200, "risk_rate": 0.21, "city": "Bogota"},
            {"id": "UDEA", "name": "Universidad de Antioquia", "students": 2800, "risk_rate": 0.18, "city": "Medellin"},
            {"id": "UDISTRITAL", "name": "U. Distrital", "students": 2100, "risk_rate": 0.24, "city": "Bogota"},
            {"id": "ITBA", "name": "ITBA", "students": 1850, "risk_rate": 0.16, "city": "Barranquilla"},
            {"id": "UNICAUCA", "name": "U. del Cauca", "students": 1400, "risk_rate": 0.29, "city": "Popayan"},
        ]
    }

@app.get("/api/dashboard/health-check-all")
async def health_check_all():
    """Check health of all dependent services"""
    services = {
        "analytics-service": ANALYTICS_SERVICE_URL,
        "alert-service": ALERT_SERVICE_URL,
        "event-service": EVENT_SERVICE_URL,
    }
    results = {}
    async with httpx.AsyncClient(timeout=3) as client:
        for name, url in services.items():
            try:
                resp = await client.get(f"{url}/health")
                results[name] = resp.json()
            except Exception as e:
                results[name] = {"status": "unreachable", "error": str(e)}
    return results

def _mock_stats():
    return {
        "total_students": 12450,
        "students_high_risk": 1876,
        "students_medium_risk": 3210,
        "students_low_risk": 7364,
        "active_alerts": 234,
        "institutions_count": 47,
        "national_dropout_rate": 0.187,
        "weekly_events": 98432,
        "risk_trend": [
            {"week": "Sem 1", "high": 120, "medium": 280, "low": 600},
            {"week": "Sem 2", "high": 145, "medium": 310, "low": 545},
            {"week": "Sem 3", "high": 189, "medium": 295, "low": 516},
            {"week": "Sem 4", "high": 201, "medium": 330, "low": 469},
            {"week": "Sem 5", "high": 187, "medium": 321, "low": 492},
            {"week": "Sem 6", "high": 220, "medium": 340, "low": 440},
        ],
        "top_risk_courses": [
            {"course": "Calculo I", "risk_rate": 0.34},
            {"course": "Programacion I", "risk_rate": 0.28},
            {"course": "Algebra Lineal", "risk_rate": 0.25},
            {"course": "IA Fundamentos", "risk_rate": 0.22},
            {"course": "Estadistica", "risk_rate": 0.19},
        ],
        "cluster_distribution": [
            {"cluster": "Alto rendimiento", "count": 4200, "pct": 33.7},
            {"cluster": "Riesgo moderado", "count": 3860, "pct": 31.0},
            {"cluster": "En riesgo", "count": 2890, "pct": 23.2},
            {"cluster": "Critico", "count": 1500, "pct": 12.1},
        ]
    }
