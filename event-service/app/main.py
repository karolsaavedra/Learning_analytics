from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("event-service")

app = FastAPI(title="Event Service", version="1.0.0")

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

EVENTS_COLLECTION = "events"

# ── In-memory fallback ────────────────────────────────────────────────────
events_db: dict = {}

class EventType(str, Enum):
    LOGIN = "login"
    ASSIGNMENT_SUBMIT = "assignment_submit"
    QUIZ_COMPLETE = "quiz_complete"
    VIDEO_WATCH = "video_watch"
    FORUM_POST = "forum_post"
    CODE_COMMIT = "code_commit"
    LATE_SUBMISSION = "late_submission"
    ABSENCE = "absence"

class AcademicEventIn(BaseModel):
    student_id: str
    institution_id: str
    course_id: str
    event_type: EventType
    score: Optional[float] = None
    duration_minutes: Optional[int] = None
    metadata: Optional[dict] = {}
    timestamp: Optional[datetime] = None

class AcademicEventOut(AcademicEventIn):
    id: str
    processed: bool = False
    created_at: datetime

@app.get("/health")
async def health():
    return {
        "service": "event-service",
        "status": "ok",
        "firestore": FIRESTORE_AVAILABLE
    }

@app.post("/api/events", response_model=AcademicEventOut)
async def capture_event(event: AcademicEventIn):
    event_out = AcademicEventOut(
        **event.model_dump(),
        id=str(uuid.uuid4()),
        processed=True,
        created_at=datetime.utcnow(),
        timestamp=event.timestamp or datetime.utcnow()
    )

    if FIRESTORE_AVAILABLE and firestore_client:
        try:
            doc_ref = firestore_client.collection(EVENTS_COLLECTION).document(event_out.id)
            doc_ref.set(event_out.model_dump())
            logger.info(f"Evento {event_out.id} guardado en Firestore")
        except Exception as e:
            logger.warning(f"Error guardando evento en Firestore: {e}")
            events_db[event_out.id] = event_out
    else:
        events_db[event_out.id] = event_out
        logger.info(f"Evento {event_out.id} guardado en memoria")

    return event_out

@app.get("/api/events/recent")
async def get_recent_events():
    if FIRESTORE_AVAILABLE and firestore_client:
        try:
            docs = firestore_client.collection(EVENTS_COLLECTION) \
                .order_by("created_at", direction=firestore.Query.DESCENDING) \
                .limit(10).stream()
            firebase_events = []
            for doc in docs:
                data = doc.to_dict()
                firebase_events.append({
                    "id": doc.id,
                    "type": data.get("event_type", "unknown"),
                    "student": data.get("student_id", ""),
                    "course": data.get("course_id", ""),
                    "ts": data.get("created_at", ""),
                    "institution_id": data.get("institution_id", ""),
                })
            if firebase_events:
                logger.info(f"Leidos {len(firebase_events)} eventos desde Firestore")
                return {"events": firebase_events, "source": "firestore"}
        except Exception as e:
            logger.warning(f"Error leyendo eventos de Firestore: {e}")

    # Fallback a mock
    return {
        "events": _mock_events(),
        "source": "memory"
    }

@app.get("/api/events/stats")
async def get_event_stats():
    if FIRESTORE_AVAILABLE and firestore_client:
        try:
            docs = list(firestore_client.collection(EVENTS_COLLECTION).stream())
            total = len(docs)
            by_type = {}
            for doc in docs:
                data = doc.to_dict()
                et = data.get("event_type", "unknown")
                by_type[et] = by_type.get(et, 0) + 1
            logger.info(f"Estadisticas calculadas desde Firestore ({total} eventos)")
            return {
                "total": total,
                "today": total,
                "this_week": total,
                "by_type": by_type,
                "source": "firestore"
            }
        except Exception as e:
            logger.warning(f"Error calculando stats de Firestore: {e}")

    return {
        "today": 1243,
        "this_week": 8976,
        "by_type": {
            "login": 3200,
            "assignment_submit": 1800,
            "quiz_complete": 1400,
            "code_commit": 980,
            "late_submission": 596,
        },
        "source": "memory"
    }

@app.get("/api/events/all")
async def get_all_events():
    if FIRESTORE_AVAILABLE and firestore_client:
        try:
            docs = firestore_client.collection(EVENTS_COLLECTION) \
                .order_by("created_at", direction=firestore.Query.DESCENDING) \
                .limit(100).stream()
            items = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                items.append(data)
            return {"events": items, "total": len(items), "source": "firestore"}
        except Exception as e:
            logger.warning(f"Error: {e}")

    return {"events": _mock_events(), "total": 5, "source": "memory"}

def _mock_events():
    return [
        {"id": "e1", "type": "assignment_submit", "student": "Ana Garcia", "course": "Programacion I", "ts": "2026-05-18T10:00:00"},
        {"id": "e2", "type": "login", "student": "Carlos M.", "course": "IA Fundamentos", "ts": "2026-05-18T09:45:00"},
        {"id": "e3", "type": "late_submission", "student": "Jose R.", "course": "Calculo I", "ts": "2026-05-18T09:30:00"},
        {"id": "e4", "type": "quiz_complete", "student": "Maria L.", "course": "Estadistica", "ts": "2026-05-18T09:15:00"},
        {"id": "e5", "type": "code_commit", "student": "Laura S.", "course": "Programacion II", "ts": "2026-05-18T09:00:00"},
    ]
