"""
Institution Service Router
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_institutions():
    return {
        "institutions": [
            {"id": "UNAL", "name": "Universidad Nacional de Colombia", "city": "Bogotá", "active": True},
            {"id": "UDEA", "name": "Universidad de Antioquia", "city": "Medellín", "active": True},
            {"id": "UDISTRITAL", "name": "Universidad Distrital", "city": "Bogotá", "active": True},
            {"id": "ITBA", "name": "ITBA", "city": "Barranquilla", "active": True},
            {"id": "UNICAUCA", "name": "Universidad del Cauca", "city": "Popayán", "active": True},
        ]
    }


@router.get("/{institution_id}/stats")
async def get_institution_stats(institution_id: str):
    return {
        "institution_id": institution_id,
        "total_students": 2500,
        "students_at_risk": 420,
        "avg_risk_score": 0.31,
        "dropout_rate": 0.18,
        "top_risk_courses": ["Cálculo I", "Programación I", "Álgebra"]
    }
