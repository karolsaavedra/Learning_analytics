from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alert-service")

app = FastAPI(title="Alert Service", version="1.0.0")

# In-memory database (Database per Service pattern)
alerts_db = {}

class AlertCreate(BaseModel):
    student_id: str
    student_name: str = "Estudiante"
    institution_id: str
    risk_level: str
    risk_score: float = 0.0
    factors: List[str] = []
    dropout_probability: float = 0.0

class AlertOut(BaseModel):
    id: str
    student_id: str
    student_name: str
    institution_id: str
    risk_level: str
    message: str
    factors: List[str]
    read: bool = False
    created_at: datetime

ALERT_MESSAGES = {
    "medium": "El estudiante presenta indicadores de riesgo academico moderado. Se recomienda seguimiento.",
    "high": "El estudiante presenta alto riesgo academico. Se requiere intervencion inmediata.",
    "critical": "ALERTA CRITICA: El estudiante esta en riesgo inminente de desercion.",
}

@app.get("/health")
async def health():
    return {"service": "alert-service", "status": "ok"}

@app.get("/api/alerts")
async def get_alerts():
    logger.info(f"Fetching alerts, total: {len(alerts_db)}")
    alerts = list(alerts_db.values()) if alerts_db else _get_mock_alerts()
    return {"alerts": [a.model_dump() for a in alerts], "total": len(alerts)}

@app.get("/api/alerts/unread-count")
async def get_unread_count():
    alerts = list(alerts_db.values()) if alerts_db else _get_mock_alerts()
    unread = sum(1 for a in alerts if not a.read)
    return {"unread": unread}

@app.post("/api/alerts/generate")
async def generate_alert(data: AlertCreate):
    risk_level = data.risk_level
    if risk_level == "low":
        logger.info(f"Risk level too low for student {data.student_id}, no alert generated")
        return {"generated": False, "reason": "Risk level too low"}

    alert = AlertOut(
        id=str(uuid.uuid4()),
        student_id=data.student_id,
        student_name=data.student_name,
        institution_id=data.institution_id,
        risk_level=risk_level,
        message=ALERT_MESSAGES.get(risk_level, "Riesgo academico detectado."),
        factors=data.factors,
        read=False,
        created_at=datetime.utcnow()
    )
    alerts_db[alert.id] = alert
    logger.info(f"Alert {alert.id} generated for student {data.student_id}")
    return {"alert": alert.model_dump(), "generated": True}

@app.put("/api/alerts/{alert_id}/read")
async def mark_read(alert_id: str):
    if alert_id in alerts_db:
        alerts_db[alert_id].read = True
        logger.info(f"Alert {alert_id} marked as read")
    return {"id": alert_id, "read": True}

@app.post("/api/alerts/seed")
async def seed_alerts():
    count = 0
    for alert in _get_mock_alerts():
        alerts_db[alert.id] = alert
        count += 1
    logger.info(f"Seeded {count} mock alerts")
    return {"seeded": count}

def _get_mock_alerts() -> List[AlertOut]:
    now = datetime.utcnow()
    return [
        AlertOut(id="a1", student_id="s001", student_name="Ana Garcia", institution_id="UNAL",
                 risk_level="critical", message="ALERTA CRITICA: Riesgo inminente de desercion.",
                 factors=["Promedio 2.8", "Asistencia 45%", "Sin entregas en 3 semanas"], read=False, created_at=now),
        AlertOut(id="a2", student_id="s002", student_name="Carlos Martinez", institution_id="UDEA",
                 risk_level="high", message="Alto riesgo academico detectado.",
                 factors=["7 entregas tardias", "Login frecuencia baja"], read=False, created_at=now),
        AlertOut(id="a3", student_id="s003", student_name="Maria Lopez", institution_id="UNAL",
                 risk_level="medium", message="Riesgo moderado. Se recomienda seguimiento.",
                 factors=["Asistencia 68%", "Promedio 3.2"], read=True, created_at=now),
        AlertOut(id="a4", student_id="s004", student_name="Jose Rodriguez", institution_id="ITBA",
                 risk_level="high", message="Disminucion significativa en actividad academica.",
                 factors=["Sin acceso en 10 dias", "Entregas tardias"], read=False, created_at=now),
        AlertOut(id="a5", student_id="s005", student_name="Laura Sanchez", institution_id="UDISTRITAL",
                 risk_level="medium", message="Indicadores de riesgo moderado detectados.",
                 factors=["Baja participacion en foros", "Tiempo de conexion reducido"], read=False, created_at=now),
    ]
