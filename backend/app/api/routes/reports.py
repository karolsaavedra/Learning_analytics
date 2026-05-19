"""
Report Service Router — National Evidence for Public Policy
"""
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/national")
async def get_national_report():
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
            {"program": "Ingeniería de Sistemas", "dropout_rate": 0.22},
            {"program": "IA & Data Science", "dropout_rate": 0.18},
            {"program": "Tecnología en Programación", "dropout_rate": 0.31},
        ],
        "recommendations": [
            "Reforzar tutorías en cursos de primer semestre",
            "Implementar mentorías en cursos con tasa de riesgo >25%",
            "Ampliar horas de acceso a laboratorios de cómputo",
        ]
    }


@router.get("/export")
async def export_report():
    return {"status": "Report generation queued", "job_id": "rpt_20260518_001"}
