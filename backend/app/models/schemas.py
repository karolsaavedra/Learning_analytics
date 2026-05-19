"""
Domain Models — Pydantic schemas for data validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventType(str, Enum):
    LOGIN = "login"
    ASSIGNMENT_SUBMIT = "assignment_submit"
    QUIZ_COMPLETE = "quiz_complete"
    VIDEO_WATCH = "video_watch"
    FORUM_POST = "forum_post"
    CODE_COMMIT = "code_commit"
    LATE_SUBMISSION = "late_submission"
    ABSENCE = "absence"


# ── Academic Event ──────────────────────────────────────────────────────────
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


# ── Student ──────────────────────────────────────────────────────────────────
class StudentProfile(BaseModel):
    student_id: str
    name: str
    institution_id: str
    program: str
    semester: int
    avg_score: float = 0.0
    attendance_rate: float = 0.0
    submissions_on_time: int = 0
    late_submissions: int = 0
    login_frequency: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    risk_score: float = 0.0


# ── Prediction ───────────────────────────────────────────────────────────────
class PredictionResult(BaseModel):
    student_id: str
    institution_id: str
    risk_score: float = Field(..., ge=0, le=1)
    risk_level: RiskLevel
    dropout_probability: float
    factors: List[str] = []
    cluster_id: Optional[int] = None
    predicted_at: datetime


# ── Alert ────────────────────────────────────────────────────────────────────
class AlertOut(BaseModel):
    id: str
    student_id: str
    student_name: str
    institution_id: str
    risk_level: RiskLevel
    message: str
    factors: List[str]
    read: bool = False
    created_at: datetime


# ── Institution ──────────────────────────────────────────────────────────────
class InstitutionStats(BaseModel):
    institution_id: str
    name: str
    total_students: int
    students_at_risk: int
    avg_risk_score: float
    dropout_rate: float
    top_risk_courses: List[str]


# ── Dashboard ────────────────────────────────────────────────────────────────
class DashboardSummary(BaseModel):
    total_students: int
    students_high_risk: int
    students_medium_risk: int
    students_low_risk: int
    active_alerts: int
    institutions_count: int
    national_dropout_rate: float
    weekly_events: int


# ── Report ───────────────────────────────────────────────────────────────────
class ReportRequest(BaseModel):
    institution_id: Optional[str] = None
    date_from: datetime
    date_to: datetime
    include_predictions: bool = True
    include_alerts: bool = True
