from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("event-service")

app = FastAPI(title="Event Service", version="1.0.0")

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
    return {"service": "event-service", "status": "ok"}

@app.post("/api/events", response_model=AcademicEventOut)
async def capture_event(event: AcademicEventIn):
    logger.info(f"Event captured: {event.event_type} for student {event.student_id}")
    return AcademicEventOut(
        **event.model_dump(),
        id=str(uuid.uuid4()),
        processed=True,
        created_at=datetime.utcnow(),
        timestamp=event.timestamp or datetime.utcnow()
    )

@app.get("/api/events/recent")
async def get_recent_events():
    logger.info("Fetching recent events")
    return {
        "events": [
            {"id": "e1", "type": "assignment_submit", "student": "Ana Garcia", "course": "Programacion I", "ts": "2026-05-18T10:00:00"},
            {"id": "e2", "type": "login", "student": "Carlos M.", "course": "IA Fundamentos", "ts": "2026-05-18T09:45:00"},
            {"id": "e3", "type": "late_submission", "student": "Jose R.", "course": "Calculo I", "ts": "2026-05-18T09:30:00"},
            {"id": "e4", "type": "quiz_complete", "student": "Maria L.", "course": "Estadistica", "ts": "2026-05-18T09:15:00"},
            {"id": "e5", "type": "code_commit", "student": "Laura S.", "course": "Programacion II", "ts": "2026-05-18T09:00:00"},
        ]
    }

@app.get("/api/events/stats")
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
