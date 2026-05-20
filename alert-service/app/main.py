from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alert-service")

app = FastAPI(title="Alert Service", version="1.0.0")

# ── Firebase Firestore (persistencia real) ────────────────────────────────
firestore_client = None
FIRESTORE_AVAILABLE = False
SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT", "")

if SERVICE_ACCOUNT_PATH and os.path.exists(SERVICE_ACCOUNT_PATH):
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)
        firestore_client = firestore.client()
        FIRESTORE_AVAILABLE = True
        logger.info("Firebase Firestore conectado exitosamente")
    except Exception as e:
        logger.warning(f"Error al conectar Firebase: {e}")
else:
    logger.info("Firebase no configurado. Usando DB en memoria.")

ALERTS_COLLECTION = "alerts"

# ── In-memory fallback ────────────────────────────────────────────────────
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
    return {
        "service": "alert-service",
        "status": "ok",
        "firestore": FIRESTORE_AVAILABLE
    }

@app.get("/api/alerts")
@app.get("/api/alerts/")
async def get_alerts():
    if FIRESTORE_AVAILABLE and firestore_client:
        try:
            docs = list(firestore_client.collection(ALERTS_COLLECTION).limit(50).stream())
            alerts = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                alerts.append(data)
            # Ordenar en Python (evita composite index en Firestore)
            alerts.sort(key=lambda a: a.get("created_at", ""), reverse=True)
            logger.info(f"Leidas {len(alerts)} alertas desde Firestore")
            return {"alerts": alerts, "total": len(alerts), "source": "firestore"}
        except Exception as e:
            logger.warning(f"Error leyendo de Firestore: {e}")

    alerts = list(alerts_db.values()) if alerts_db else _get_mock_alerts()
    return {"alerts": [a.model_dump() for a in alerts], "total": len(alerts), "source": "memory"}

@app.get("/api/alerts/unread-count")
@app.get("/api/alerts/unread-count/")
async def get_unread_count():
    if FIRESTORE_AVAILABLE and firestore_client:
        try:
            docs = firestore_client.collection(ALERTS_COLLECTION) \
                .where("read", "==", False).stream()
            count = sum(1 for _ in docs)
            return {"unread": count, "source": "firestore"}
        except Exception as e:
            logger.warning(f"Error contando en Firestore: {e}")

    alerts = list(alerts_db.values()) if alerts_db else _get_mock_alerts()
    unread = sum(1 for a in alerts if not a.read)
    return {"unread": unread, "source": "memory"}

@app.post("/api/alerts/generate")
async def generate_alert(data: AlertCreate):
    risk_level = data.risk_level
    if risk_level == "low" and data.risk_score < 0.25:
        logger.info(f"Risk too low for student {data.student_id} (score={data.risk_score})")
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

    if FIRESTORE_AVAILABLE and firestore_client:
        try:
            doc_ref = firestore_client.collection(ALERTS_COLLECTION).document(alert.id)
            doc_ref.set(alert.model_dump())
            logger.info(f"Alerta {alert.id} guardada en Firestore")
            return {"alert": alert.model_dump(), "generated": True, "source": "firestore"}
        except Exception as e:
            logger.warning(f"Error guardando en Firestore: {e}")

    alerts_db[alert.id] = alert
    logger.info(f"Alerta {alert.id} guardada en memoria")
    return {"alert": alert.model_dump(), "generated": True, "source": "memory"}

@app.put("/api/alerts/{alert_id}/read")
async def mark_read(alert_id: str):
    if FIRESTORE_AVAILABLE and firestore_client:
        try:
            firestore_client.collection(ALERTS_COLLECTION).document(alert_id).update({"read": True})
            logger.info(f"Alerta {alert_id} marcada como leida en Firestore")
            return {"id": alert_id, "read": True, "source": "firestore"}
        except Exception as e:
            logger.warning(f"Error actualizando en Firestore: {e}")

    if alert_id in alerts_db:
        alerts_db[alert_id].read = True
    return {"id": alert_id, "read": True, "source": "memory"}

@app.post("/api/alerts/seed")
async def seed_alerts():
    count = 0
    for alert in _get_mock_alerts():
        if FIRESTORE_AVAILABLE and firestore_client:
            try:
                firestore_client.collection(ALERTS_COLLECTION).document(alert.id).set(alert.model_dump())
                count += 1
            except:
                pass
        else:
            alerts_db[alert.id] = alert
            count += 1
    logger.info(f"Seeded {count} alertas")
    return {"seeded": count, "source": "firestore" if FIRESTORE_AVAILABLE else "memory"}

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
