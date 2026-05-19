"""
Dashboard Service Router
"""
from fastapi import APIRouter
from app.viewmodels.analytics_vm import analytics_vm

router = APIRouter()


@router.get("/summary")
async def get_dashboard_summary():
    stats = analytics_vm.generate_mock_stats()
    return stats


@router.get("/institutions")
async def get_institutions_overview():
    return {
        "institutions": [
            {"id": "UNAL", "name": "Universidad Nacional", "students": 3200, "risk_rate": 0.21, "city": "Bogotá"},
            {"id": "UDEA", "name": "Universidad de Antioquia", "students": 2800, "risk_rate": 0.18, "city": "Medellín"},
            {"id": "UDISTRITAL", "name": "U. Distrital", "students": 2100, "risk_rate": 0.24, "city": "Bogotá"},
            {"id": "ITBA", "name": "ITBA", "students": 1850, "risk_rate": 0.16, "city": "Barranquilla"},
            {"id": "UNICAUCA", "name": "U. del Cauca", "students": 1400, "risk_rate": 0.29, "city": "Popayán"},
        ]
    }
