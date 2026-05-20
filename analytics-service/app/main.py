from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Optional
import logging
import httpx
import os

from app.viewmodel import analytics_vm, StudentProfile, PredictionResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("analytics-service")

app = FastAPI(title="Analytics Service", version="1.0.0")

ALERT_SERVICE_URL = os.getenv("ALERT_SERVICE_URL", "http://alert-service:8003")

class PredictRequest(BaseModel):
    student_id: str
    institution_id: str
    avg_score: float = Field(..., ge=0, le=10)
    attendance_rate: float = Field(..., ge=0, le=1)
    late_submissions: int = Field(..., ge=0)
    login_frequency: float = Field(..., ge=0, le=7)

@app.get("/health")
async def health():
    return {"service": "analytics-service", "status": "ok"}

@app.post("/api/analytics/predict")
async def predict_risk(req: PredictRequest):
    logger.info(f"Predicting risk for student {req.student_id}")
    profile = StudentProfile(
        student_id=req.student_id,
        institution_id=req.institution_id,
        avg_score=req.avg_score,
        attendance_rate=req.attendance_rate,
        late_submissions=req.late_submissions,
        login_frequency=req.login_frequency,
    )
    result = analytics_vm.predict_student_risk(profile)

    pred_dict = {
        "student_id": result.student_id,
        "institution_id": result.institution_id,
        "risk_score": result.risk_score,
        "risk_level": result.risk_level.value,
        "dropout_probability": result.dropout_probability,
        "factors": result.factors,
        "cluster_id": result.cluster_id,
    }

    # Communicate with alert-service: if risk >= MEDIUM, generate alert
    if result.risk_level.value in ("medium", "high", "critical"):
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                alert_resp = await client.post(
                    f"{ALERT_SERVICE_URL}/api/alerts/generate",
                    json={**pred_dict, "student_name": f"Student_{req.student_id}"},
                )
                if alert_resp.status_code == 200:
                    alert_data = alert_resp.json()
                    pred_dict["alert_generated"] = alert_data.get("generated", False)
                    logger.info(f"Alert generated for student {req.student_id}")
        except Exception as e:
            logger.warning(f"Alert service unavailable: {e}")
            pred_dict["alert_generated"] = False
            pred_dict["alert_error"] = str(e)

    return pred_dict

@app.get("/api/analytics/stats")
async def get_stats():
    logger.info("Fetching analytics stats")
    return analytics_vm.generate_mock_stats()

@app.get("/api/analytics/clusters")
async def get_clusters():
    return analytics_vm.get_cluster_summary()

@app.get("/api/analytics/trends")
async def get_trends():
    stats = analytics_vm.generate_mock_stats()
    return {"trend": stats["risk_trend"]}

@app.get("/api/analytics/top-risk-courses")
async def get_top_courses():
    stats = analytics_vm.generate_mock_stats()
    return {"courses": stats["top_risk_courses"]}
