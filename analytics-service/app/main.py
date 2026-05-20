from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging
import httpx
import os
import uuid

from app.viewmodel import analytics_vm, StudentProfile, PredictionResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("analytics-service")

app = FastAPI(title="Analytics Service", version="1.0.0")

ALERT_SERVICE_URL = os.getenv("ALERT_SERVICE_URL", "http://alert-service:8003")

# ── Firebase Firestore ────────────────────────────────────────────────────
firestore_client = None
FIRESTORE_AVAILABLE = False
SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT", "")
db = None

if SERVICE_ACCOUNT_PATH and os.path.exists(SERVICE_ACCOUNT_PATH):
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        FIRESTORE_AVAILABLE = True
        logger.info("Firebase Firestore conectado exitosamente")
    except Exception as e:
        logger.warning(f"Error al conectar Firebase: {e}")
else:
    logger.info("Firebase no configurado. Usando DB en memoria.")

class PredictRequest(BaseModel):
    student_id: str = ""
    student_name: str = "Estudiante"
    institution_id: str
    program: str = "General"
    semester: int = 1
    avg_score: float = Field(..., ge=0, le=10)
    attendance_rate: float = Field(..., ge=0, le=1)
    late_submissions: int = Field(..., ge=0)
    login_frequency: float = Field(..., ge=0, le=7)

class CourseIn(BaseModel):
    course: str
    risk_rate: float = Field(..., ge=0, le=1)

@app.get("/health")
async def health():
    return {"service": "analytics-service", "status": "ok", "firestore": FIRESTORE_AVAILABLE}

def _slug(name: str) -> str:
    import re
    s = name.lower().strip().replace(" ", "_")
    s = re.sub(r'[^a-z0-9_]', '', s)
    return s

@app.post("/api/analytics/predict")
async def predict_risk(req: PredictRequest):
    # Generar student_id desde el nombre
    student_id = req.student_id or f"s_{_slug(req.student_name)}_{_slug(req.institution_id)}"
    logger.info(f"Predicting risk for {req.student_name} ({student_id})")

    # ── Verificar / crear estudiante en Firestore ────────────────────────────
    student_created = False
    if FIRESTORE_AVAILABLE and db:
        try:
            existing = db.collection("students").document(student_id).get()
            if not existing.exists:
                student_data = {
                    "id": student_id,
                    "name": req.student_name,
                    "institution_id": req.institution_id,
                    "program": req.program,
                    "semester": req.semester,
                    "avg_score": req.avg_score,
                    "attendance_rate": req.attendance_rate,
                    "late_submissions": req.late_submissions,
                    "login_frequency": req.login_frequency,
                    "created_at": datetime.utcnow().isoformat(),
                }
                db.collection("students").document(student_id).set(student_data)
                student_created = True
                logger.info(f"Estudiante {student_id} creado en Firestore")
            else:
                # Actualizar datos academicos
                db.collection("students").document(student_id).update({
                    "avg_score": req.avg_score,
                    "attendance_rate": req.attendance_rate,
                    "late_submissions": req.late_submissions,
                    "login_frequency": req.login_frequency,
                    "semester": req.semester,
                    "last_prediction": datetime.utcnow().isoformat(),
                })
                logger.info(f"Estudiante {student_id} actualizado en Firestore")
        except Exception as e:
            logger.warning(f"Error con estudiante en Firestore: {e}")

    # ── Ejecutar prediccion ──────────────────────────────────────────────────
    profile = StudentProfile(
        student_id=student_id,
        institution_id=req.institution_id,
        avg_score=req.avg_score,
        attendance_rate=req.attendance_rate,
        late_submissions=req.late_submissions,
        login_frequency=req.login_frequency,
    )
    result = analytics_vm.predict_student_risk(profile)

    pred_dict = {
        "student_id": student_id,
        "student_name": req.student_name,
        "institution_id": result.institution_id,
        "program": req.program,
        "semester": req.semester,
        "risk_score": result.risk_score,
        "risk_level": result.risk_level.value,
        "dropout_probability": result.dropout_probability,
        "factors": result.factors,
        "cluster_id": result.cluster_id,
        "predicted_at": datetime.utcnow().isoformat(),
        "student_created": student_created,
    }

    # ── Guardar prediccion en Firestore ──────────────────────────────────────
    if FIRESTORE_AVAILABLE and db:
        try:
            db.collection("predictions").document(str(uuid.uuid4())).set(pred_dict)
            logger.info(f"Prediccion guardada en Firestore")
        except Exception as e:
            logger.warning(f"Error guardando prediccion: {e}")

    # ── Generar alerta si riesgo es medio o superior (o borderline) ────────
    if result.risk_level.value in ("medium", "high", "critical") or result.risk_score >= 0.25:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                alert_resp = await client.post(
                    f"{ALERT_SERVICE_URL}/api/alerts/generate",
                    json={**pred_dict, "student_name": req.student_name, "student_id": student_id},
                )
                if alert_resp.status_code == 200:
                    pred_dict["alert_generated"] = alert_resp.json().get("generated", False)
        except Exception as e:
            logger.warning(f"Alert service unavailable: {e}")
            pred_dict["alert_generated"] = False

    return pred_dict

@app.get("/api/analytics/stats")
async def get_stats():
    """Calcula estadisticas desde Firestore con fallback a mock"""
    stats = _mock_stats()

    if not (FIRESTORE_AVAILABLE and db):
        logger.info("Firestore no disponible, usando datos mock")
        return stats

    try:
        # ── Contar estudiantes desde Firestore ──────────────────────────────
        students_snapshot = list(db.collection("students").stream())
        real_students = len(students_snapshot)
        if real_students > 0:
            stats["total_students"] = real_students

            # Calcular niveles de riesgo basados en avg_score
            high = sum(1 for s in students_snapshot if s.to_dict().get("avg_score", 5) < 4)
            low = sum(1 for s in students_snapshot if s.to_dict().get("avg_score", 5) >= 7)
            medium = real_students - high - low
            stats["students_high_risk"] = high
            stats["students_medium_risk"] = max(0, medium)
            stats["students_low_risk"] = max(0, low)
    except Exception as e:
        logger.warning(f"Error contando estudiantes: {e}")

    try:
        # ── Contar predicciones desde Firestore ─────────────────────────────
        preds_snapshot = list(db.collection("predictions").stream())
        real_preds = len(preds_snapshot)
        if real_preds > 0:
            risk_scores = [p.to_dict().get("risk_score", 0) for p in preds_snapshot]
            avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0
            stats["national_dropout_rate"] = round(avg_risk, 3)

            # Calcular tendencia semanal desde predicciones
            from collections import defaultdict
            weeks = defaultdict(lambda: {"high": 0, "medium": 0, "low": 0})
            for p in preds_snapshot:
                data = p.to_dict()
                level = data.get("risk_level", "low")
                week = f"Sem {(len(preds_snapshot) // 100) + 1}"
                if level == "critical":
                    weeks[week]["high"] += 1
                elif level == "high":
                    weeks[week]["high"] += 1
                elif level == "medium":
                    weeks[week]["medium"] += 1
                else:
                    weeks[week]["low"] += 1

            if weeks:
                stats["risk_trend"] = [
                    {"week": w, **d} for w, d in sorted(weeks.items())
                ]

            # Distribucion por cluster
            cluster_counts = defaultdict(int)
            for p in preds_snapshot:
                cid = p.to_dict().get("cluster_id", 0)
                cluster_counts[cid] += 1

            total = sum(cluster_counts.values()) or 1
            cluster_names = {0: "Alto rendimiento", 1: "Riesgo moderado", 2: "En riesgo", 3: "Critico"}
            colors = {0: "33.7", 1: "31.0", 2: "23.2", 3: "12.1"}
            stats["cluster_distribution"] = [
                {"cluster": cluster_names.get(cid, f"Cluster {cid}"),
                 "count": count,
                 "pct": round(count / total * 100, 1)}
                for cid, count in sorted(cluster_counts.items())
            ]
    except Exception as e:
        logger.warning(f"Error procesando predicciones: {e}")

    try:
        # ── Contar instituciones ────────────────────────────────────────────
        inst_snapshot = list(db.collection("institutions").stream())
        if inst_snapshot:
            stats["institutions_count"] = len(inst_snapshot)
    except Exception as e:
        logger.warning(f"Error contando instituciones: {e}")

    try:
        # ── Cursos desde Firestore ──────────────────────────────────────────
        courses_docs = list(db.collection("courses").stream())
        if courses_docs:
            stats["top_risk_courses"] = [
                {"course": d.to_dict().get("course", ""),
                 "risk_rate": d.to_dict().get("risk_rate", 0)}
                for d in sorted(courses_docs,
                    key=lambda d: d.to_dict().get("risk_rate", 0), reverse=True)
            ][:5]
    except Exception as e:
        logger.warning(f"Error leyendo cursos: {e}")

    try:
        # ── Alertas activas ─────────────────────────────────────────────────
        alerts_snapshot = list(db.collection("alerts").where("read", "==", False).stream())
        if alerts_snapshot:
            stats["active_alerts"] = len(alerts_snapshot)
    except Exception as e:
        logger.warning(f"Error contando alertas: {e}")

    try:
        # ── Eventos semanales ────────────────────────────────────────────────
        events_snapshot = list(db.collection("events").stream())
        if events_snapshot:
            stats["weekly_events"] = len(events_snapshot) * 10
    except Exception as e:
        logger.warning(f"Error contando eventos: {e}")

    logger.info("Estadisticas calculadas desde Firestore")
    return stats

@app.get("/api/analytics/clusters")
async def get_clusters():
    return analytics_vm.get_cluster_summary()

@app.get("/api/analytics/trends")
async def get_trends():
    stats = await get_stats()
    return {"trend": stats.get("risk_trend", _mock_stats()["risk_trend"])}

@app.get("/api/analytics/top-risk-courses")
async def get_top_courses():
    if FIRESTORE_AVAILABLE and db:
        try:
            docs = list(db.collection("courses").stream())
            if docs:
                courses = sorted(
                    [{"course": d.to_dict().get("course"), "risk_rate": d.to_dict().get("risk_rate", 0)}
                     for d in docs],
                    key=lambda c: c["risk_rate"], reverse=True
                )
                return {"courses": courses, "source": "firestore"}
        except Exception as e:
            logger.warning(f"Error leyendo cursos: {e}")

    stats = _mock_stats()
    return {"courses": stats["top_risk_courses"], "source": "memory"}

@app.post("/api/analytics/courses")
async def create_course(course: CourseIn):
    course_id = course.course.lower().replace(" ", "_").replace("í", "i").replace("ó", "o")
    data = course.model_dump()

    if FIRESTORE_AVAILABLE and db:
        try:
            db.collection("courses").document(course_id).set(data)
            logger.info(f"Curso {course_id} creado en Firestore")
            return {"course": data, "source": "firestore"}
        except Exception as e:
            logger.warning(f"Error creando curso: {e}")

    return {"course": data, "source": "memory"}

@app.delete("/api/analytics/courses/{course_id}")
async def delete_course(course_id: str):
    if FIRESTORE_AVAILABLE and db:
        try:
            db.collection("courses").document(course_id).delete()
            return {"deleted": course_id, "source": "firestore"}
        except:
            pass
    return {"deleted": course_id, "source": "memory"}

@app.get("/api/analytics/courses/seed")
async def seed_courses():
    default_courses = [
        {"course": "Calculo I", "risk_rate": 0.34},
        {"course": "Programacion I", "risk_rate": 0.28},
        {"course": "Algebra Lineal", "risk_rate": 0.25},
        {"course": "IA Fundamentos", "risk_rate": 0.22},
        {"course": "Estadistica", "risk_rate": 0.19},
    ]
    count = 0
    for c in default_courses:
        cid = c["course"].lower().replace(" ", "_").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o")
        if FIRESTORE_AVAILABLE and db:
            try:
                db.collection("courses").document(cid).set(c)
                count += 1
            except:
                pass
    logger.info(f"Seeded {count} cursos")
    return {"seeded": count, "source": "firestore" if FIRESTORE_AVAILABLE else "memory"}

# ── Students ────────────────────────────────────────────────────────────────
@app.get("/api/analytics/students")
async def list_students():
    if FIRESTORE_AVAILABLE and db:
        try:
            docs = list(db.collection("students").stream())
            students = [{"id": d.id, **d.to_dict()} for d in docs]
            return {"students": students, "total": len(students), "source": "firestore"}
        except Exception as e:
            logger.warning(f"Error leyendo estudiantes: {e}")
    return {"students": _mock_students(), "total": 5, "source": "memory"}

@app.get("/api/analytics/predictions")
async def list_predictions():
    if FIRESTORE_AVAILABLE and db:
        try:
            docs = list(db.collection("predictions").stream())
            preds = [{"id": d.id, **d.to_dict()} for d in docs]
            return {"predictions": preds, "total": len(preds), "source": "firestore"}
        except Exception as e:
            logger.warning(f"Error leyendo predicciones: {e}")
    return {"predictions": [], "total": 0, "source": "memory"}

# ── Risk calculation for a specific institution ──────────────────────────────
@app.get("/api/analytics/institution-risk/{institution_id}")
async def get_institution_risk(institution_id: str):
    """Calcula risk_rate real para una institucion basado en predicciones"""
    if FIRESTORE_AVAILABLE and db:
        try:
            docs = list(db.collection("predictions")
                .where("institution_id", "==", institution_id).stream())
            if docs:
                scores = [d.to_dict().get("risk_score", 0) for d in docs]
                avg_risk = round(sum(scores) / len(scores), 4)
                total_students = len(set(d.to_dict().get("student_id") for d in docs))
                return {
                    "institution_id": institution_id,
                    "risk_rate": avg_risk,
                    "total_predictions": len(docs),
                    "total_students": total_students,
                    "source": "firestore"
                }
        except Exception as e:
            logger.warning(f"Error calculando riesgo: {e}")

    # Fallback: calcular desde estudiantes mock
    students = _mock_students()
    inst_students = [s for s in students if s.get("institution_id") == institution_id]
    if inst_students:
        scores = [profile_to_risk(s) for s in inst_students]
        avg = round(sum(scores) / len(scores), 4)
        return {"institution_id": institution_id, "risk_rate": avg, "total_students": len(inst_students), "source": "memory"}
    return {"institution_id": institution_id, "risk_rate": 0, "total_students": 0, "source": "memory"}

def profile_to_risk(student: dict) -> float:
    score = student.get("avg_score", 5)
    attend = student.get("attendance_rate", 0.7)
    risk = (1 - score / 10) * 0.5 + (1 - attend) * 0.5
    return min(1, max(0, risk))

def _mock_students():
    return [
        {"id": "s001", "name": "Ana Garcia", "institution_id": "UNAL", "avg_score": 2.8, "attendance_rate": 0.45},
        {"id": "s002", "name": "Carlos Martinez", "institution_id": "UDEA", "avg_score": 6.2, "attendance_rate": 0.72},
        {"id": "s003", "name": "Maria Lopez", "institution_id": "UNAL", "avg_score": 3.2, "attendance_rate": 0.68},
        {"id": "s004", "name": "Jose Rodriguez", "institution_id": "ITBA", "avg_score": 4.5, "attendance_rate": 0.6},
        {"id": "s005", "name": "Laura Sanchez", "institution_id": "UDISTRITAL", "avg_score": 7.8, "attendance_rate": 0.9},
    ]

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
