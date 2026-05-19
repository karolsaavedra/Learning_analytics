"""
Event Service Router — Capture academic events
"""
from fastapi import APIRouter
from datetime import datetime
import uuid

from app.models.schemas import AcademicEventIn, AcademicEventOut

router = APIRouter()


@router.post("/", response_model=AcademicEventOut)
async def capture_event(event: AcademicEventIn):
    """Capture and process an academic event"""
    return AcademicEventOut(
        **event.model_dump(),
        id=str(uuid.uuid4()),
        processed=True,
        created_at=datetime.utcnow(),
        timestamp=event.timestamp or datetime.utcnow()
    )


@router.get("/recent")
async def get_recent_events():
    """Get recent academic events (mock)"""
    return {
        "events": [
            {"id": "e1", "type": "assignment_submit", "student": "Ana García", "course": "Programación I", "ts": "2026-05-18T10:00:00"},
            {"id": "e2", "type": "login", "student": "Carlos M.", "course": "IA Fundamentos", "ts": "2026-05-18T09:45:00"},
            {"id": "e3", "type": "late_submission", "student": "José R.", "course": "Cálculo I", "ts": "2026-05-18T09:30:00"},
            {"id": "e4", "type": "quiz_complete", "student": "María L.", "course": "Estadística", "ts": "2026-05-18T09:15:00"},
            {"id": "e5", "type": "code_commit", "student": "Laura S.", "course": "Programación II", "ts": "2026-05-18T09:00:00"},
        ]
    }


@router.get("/stats")
async def get_event_stats():
    return {
        "today": 1243,
        "this_week": 8976,
        "by_type": {
            "login": 3200,
            "assignment_submit": 1800,
            "quiz_complete": 1400,
            "code_commit": 980,
            "late_submission": 596,
        }
    }
