from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging
import httpx
import os
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dashboard-service")

app = FastAPI(title="Dashboard Service", version="1.0.0")

ANALYTICS_SERVICE_URL = os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service:8002")
ALERT_SERVICE_URL = os.getenv("ALERT_SERVICE_URL", "http://alert-service:8003")
EVENT_SERVICE_URL = os.getenv("EVENT_SERVICE_URL", "http://event-service:8001")

# ── Firebase Firestore ────────────────────────────────────────────────────
db = None
FIRESTORE_AVAILABLE = False
SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT", "")

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

institutions_db = {}

class InstitutionIn(BaseModel):
    name: str
    city: str
    students: int = 0
    risk_rate: float = 0.0
    active: bool = True

class StudentIn(BaseModel):
    name: str
    institution_id: str
    program: str
    semester: int = 1
    avg_score: float = 0.0
    attendance_rate: float = 0.0

@app.get("/health")
async def health():
    return {"service": "dashboard-service", "status": "ok", "firestore": FIRESTORE_AVAILABLE}

# ── Dashboard Summary (Aggregator + Firestore real) ────────────────────────
@app.get("/api/dashboard/summary")
async def get_dashboard_summary():
    logger.info("Aggregating dashboard summary")

    stats = None
    alerts_data = None

    async with httpx.AsyncClient(timeout=5) as client:
        try:
            resp = await client.get(f"{ANALYTICS_SERVICE_URL}/api/analytics/stats")
            stats = resp.json()
        except Exception as e:
            logger.warning(f"analytics-service unavailable: {e}")
        try:
            resp = await client.get(f"{ALERT_SERVICE_URL}/api/alerts/unread-count")
            alerts_data = resp.json()
        except Exception as e:
            logger.warning(f"alert-service unavailable: {e}")

    result = stats or _mock_stats()

    if alerts_data:
        result["active_alerts"] = alerts_data.get("unread", 234)

    # institutions_count real desde Firestore
    inst_count = await _count_firestore("institutions")
    if inst_count and inst_count > 0:
        result["institutions_count"] = inst_count

    return result

# ── Institutions CRUD con risk_rate automatico ──────────────────────────────
@app.get("/api/institutions")
async def list_institutions():
    if FIRESTORE_AVAILABLE and db:
        try:
            docs = list(db.collection("institutions").stream())
            if docs:
                institutions = []
                for doc in docs:
                    data = doc.to_dict()
                    data["id"] = doc.id
                    # Calcular risk_rate real desde analytics-service
                    risk = await _calc_institution_risk(doc.id)
                    if risk is not None:
                        data["risk_rate"] = risk
                    # Contar estudiantes reales desde Firestore
                    try:
                        sdocs = list(db.collection("students").where("institution_id", "==", doc.id).stream())
                        data["students"] = len(sdocs)
                        data["student_count"] = len(sdocs)
                    except:
                        pass
                    institutions.append(data)
                return {"institutions": institutions, "source": "firestore"}
        except Exception as e:
            logger.warning(f"Error leyendo instituciones: {e}")

    insts = list(institutions_db.values()) if institutions_db else _mock_institutions()
    return {"institutions": insts, "source": "memory"}

@app.post("/api/institutions")
async def create_institution(inst: InstitutionIn):
    inst_id = inst.name.lower().replace(" ", "_").replace("í", "i").replace("ó", "o")[:20]
    data = inst.model_dump()
    data["id"] = inst_id
    data["risk_rate"] = 0.0
    data["created_at"] = datetime.utcnow().isoformat()

    if FIRESTORE_AVAILABLE and db:
        try:
            db.collection("institutions").document(inst_id).set(data)
            logger.info(f"Institucion {inst_id} creada en Firestore")
            return {"institution": data, "source": "firestore"}
        except Exception as e:
            logger.warning(f"Error creando institucion: {e}")

    institutions_db[inst_id] = data
    return {"institution": data, "source": "memory"}

@app.put("/api/institutions/{inst_id}")
async def update_institution(inst_id: str, inst: InstitutionIn):
    data = inst.model_dump()
    data["id"] = inst_id
    if FIRESTORE_AVAILABLE and db:
        try:
            db.collection("institutions").document(inst_id).set(data)
            return {"institution": data, "source": "firestore"}
        except:
            pass
    institutions_db[inst_id] = data
    return {"institution": data, "source": "memory"}

@app.delete("/api/institutions/{inst_id}")
async def delete_institution(inst_id: str):
    if FIRESTORE_AVAILABLE and db:
        try:
            db.collection("institutions").document(inst_id).delete()
            return {"deleted": inst_id, "source": "firestore"}
        except:
            pass
    institutions_db.pop(inst_id, None)
    return {"deleted": inst_id, "source": "memory"}

@app.get("/api/institutions/seed")
async def seed_institutions():
    count = 0
    for inst in _mock_institutions():
        inst_id = inst["id"]
        inst["risk_rate"] = 0.0
        inst["created_at"] = datetime.utcnow().isoformat()
        if FIRESTORE_AVAILABLE and db:
            try:
                db.collection("institutions").document(inst_id).set(inst)
                count += 1
            except:
                pass
        else:
            institutions_db[inst_id] = inst
            count += 1
    logger.info(f"Seeded {count} instituciones")
    return {"seeded": count}

@app.get("/api/institutions/{institution_id}/stats")
async def get_institution_stats(institution_id: str):
    """Estadisticas reales de una institucion (risk_rate calculado)"""
    risk = await _calc_institution_risk(institution_id)
    risk_rate = risk if risk is not None else _mock_institution_risk(institution_id)

    # Contar estudiantes desde Firestore
    students_count = 0
    if FIRESTORE_AVAILABLE and db:
        try:
            sdocs = list(db.collection("students").where("institution_id", "==", institution_id).stream())
            students_count = len(sdocs)
        except:
            pass

    if students_count == 0:
        # Buscar en mock
        for inst in _mock_institutions():
            if inst["id"] == institution_id:
                students_count = inst.get("students", 2500)
                if risk is None:
                    risk_rate = inst.get("risk_rate", 0.18)
                break
        else:
            students_count = 2500

    return {
        "institution_id": institution_id,
        "total_students": students_count,
        "students_at_risk": int(students_count * risk_rate),
        "avg_risk_score": round(risk_rate, 2),
        "dropout_rate": round(risk_rate * 0.85, 3),
        "top_risk_courses": ["Calculo I", "Programacion I", "Algebra"]
    }

@app.get("/api/dashboard/institutions")
async def get_dashboard_institutions():
    return await list_institutions()

# ── Students ────────────────────────────────────────────────────────────────
@app.get("/api/students")
async def list_students():
    if FIRESTORE_AVAILABLE and db:
        try:
            docs = list(db.collection("students").stream())
            students = [{"id": d.id, **d.to_dict()} for d in docs]
            return {"students": students, "total": len(students), "source": "firestore"}
        except Exception as e:
            logger.warning(f"Error leyendo estudiantes: {e}")
    return {"students": _mock_students(), "total": 5, "source": "memory"}

@app.post("/api/students")
async def create_student(student: StudentIn):
    student_id = str(uuid.uuid4())[:8]
    data = student.model_dump()
    data["id"] = student_id
    data["created_at"] = datetime.utcnow().isoformat()
    if FIRESTORE_AVAILABLE and db:
        try:
            db.collection("students").document(student_id).set(data)
            return {"student": data, "source": "firestore"}
        except:
            pass
    return {"student": data, "source": "memory"}

@app.post("/api/students/find-or-create")
async def find_or_create_student(student: StudentIn):
    """Busca estudiante por nombre + institucion, si no existe lo crea"""
    if FIRESTORE_AVAILABLE and db:
        try:
            docs = list(db.collection("students")
                .where("name", "==", student.name)
                .where("institution_id", "==", student.institution_id)
                .limit(1).stream())
            if docs:
                existing = docs[0].to_dict()
                existing["id"] = docs[0].id
                logger.info(f"Estudiante existente encontrado: {existing['id']}")
                # Actualizar avg_score y attendance_rate
                if student.avg_score != existing.get("avg_score", 0) or student.attendance_rate != existing.get("attendance_rate", 0):
                    existing["avg_score"] = student.avg_score
                    existing["attendance_rate"] = student.attendance_rate
                    db.collection("students").document(docs[0].id).update({
                        "avg_score": student.avg_score,
                        "attendance_rate": student.attendance_rate,
                        "updated_at": datetime.utcnow().isoformat()
                    })
                return {"student": existing, "created": False, "source": "firestore"}
        except Exception as e:
            logger.warning(f"Error buscando estudiante: {e}")

    # No existe o Firestore no disponible → crear nuevo
    result = await create_student(student)
    data = result.get("student", result) if isinstance(result, dict) else result
    return {"student": data, "created": True, "source": result.get("source", "memory") if isinstance(result, dict) else "memory"}

# ── Reports ──────────────────────────────────────────────────────────────────
@app.get("/api/reports/national")
async def get_national_report():
    stats = None
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            resp = await client.get(f"{ANALYTICS_SERVICE_URL}/api/analytics/stats")
            stats = resp.json()
        except:
            pass

    inst_count = await _count_firestore("institutions")
    institutions_reporting = inst_count if inst_count and inst_count > 0 else (stats.get("institutions_count", 0) if stats else 0)

    if stats:
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "period": "2026-I",
            "summary": {
                "total_enrolled": stats.get("total_students", 125000),
                "dropout_national": stats.get("national_dropout_rate", 0.187),
                "high_risk_count": stats.get("students_high_risk", 23400),
                "institutions_reporting": institutions_reporting,
                "alerts_generated": stats.get("active_alerts", 8932),
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

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "period": "2026-I",
        "summary": {
            "total_enrolled": 125000,
            "dropout_national": 0.187,
            "high_risk_count": 23400,
            "institutions_reporting": institutions_reporting,
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

@app.get("/api/dashboard/health-check-all")
async def health_check_all():
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
            except:
                results[name] = {"status": "unreachable"}
    return results

# ── Helpers ──────────────────────────────────────────────────────────────────
async def _count_firestore(collection: str) -> Optional[int]:
    if FIRESTORE_AVAILABLE and db:
        try:
            return len(list(db.collection(collection).stream()))
        except:
            pass
    return None

async def _calc_institution_risk(institution_id: str) -> Optional[float]:
    """Calcula risk_rate llamando al analytics-service"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{ANALYTICS_SERVICE_URL}/api/analytics/institution-risk/{institution_id}"
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("risk_rate")
    except:
        pass
    return None

def _mock_institution_risk(institution_id: str) -> float:
    risks = {
        "UNAL": 0.21, "UDEA": 0.18, "UDISTRITAL": 0.24,
        "ITBA": 0.16, "UNICAUCA": 0.29,
    }
    return risks.get(institution_id, 0.2)

def _mock_institutions():
    return [
        {"id": "UNAL", "name": "Universidad Nacional de Colombia", "city": "Bogota", "students": 3200, "risk_rate": 0.21, "active": True},
        {"id": "UDEA", "name": "Universidad de Antioquia", "city": "Medellin", "students": 2800, "risk_rate": 0.18, "active": True},
        {"id": "UDISTRITAL", "name": "Universidad Distrital", "city": "Bogota", "students": 2100, "risk_rate": 0.24, "active": True},
        {"id": "ITBA", "name": "ITBA", "city": "Barranquilla", "students": 1850, "risk_rate": 0.16, "active": True},
        {"id": "UNICAUCA", "name": "Universidad del Cauca", "city": "Popayan", "students": 1400, "risk_rate": 0.29, "active": True},
    ]

def _mock_students():
    return [
        {"id": "s001", "name": "Ana Garcia", "institution_id": "UNAL", "program": "Ing. Sistemas", "semester": 3, "avg_score": 2.8, "attendance_rate": 0.45},
        {"id": "s002", "name": "Carlos Martinez", "institution_id": "UDEA", "program": "IA & Data Science", "semester": 5, "avg_score": 6.2, "attendance_rate": 0.72},
        {"id": "s003", "name": "Maria Lopez", "institution_id": "UNAL", "program": "Ing. Sistemas", "semester": 2, "avg_score": 3.2, "attendance_rate": 0.68},
        {"id": "s004", "name": "Jose Rodriguez", "institution_id": "ITBA", "program": "Tec. Programacion", "semester": 1, "avg_score": 4.5, "attendance_rate": 0.6},
        {"id": "s005", "name": "Laura Sanchez", "institution_id": "UDISTRITAL", "program": "Ciencias Computacion", "semester": 4, "avg_score": 7.8, "attendance_rate": 0.9},
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
