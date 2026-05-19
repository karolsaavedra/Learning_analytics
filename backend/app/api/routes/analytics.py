"""
Analytics Service Router — IA Predictive Analysis
"""
from fastapi import APIRouter
from app.models.schemas import StudentProfile
from app.viewmodels.analytics_vm import analytics_vm

router = APIRouter()


@router.post("/predict")
async def predict_student_risk(profile: StudentProfile):
    """Run ML risk prediction for a student"""
    result = analytics_vm.predict_student_risk(profile)
    return result


@router.get("/stats")
async def get_analytics_stats():
    """National analytics statistics"""
    return analytics_vm.generate_mock_stats()


@router.get("/clusters")
async def get_cluster_summary():
    """Get academic cluster definitions"""
    return analytics_vm.get_cluster_summary()


@router.get("/trends")
async def get_risk_trends():
    stats = analytics_vm.generate_mock_stats()
    return {"trend": stats["risk_trend"]}


@router.get("/top-risk-courses")
async def get_top_risk_courses():
    stats = analytics_vm.generate_mock_stats()
    return {"courses": stats["top_risk_courses"]}
