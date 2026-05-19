"""
Alert Service Router — Academic Alerts
"""
from fastapi import APIRouter
from app.viewmodels.alert_vm import alert_vm
from app.models.schemas import PredictionResult

router = APIRouter()


@router.get("/")
async def get_alerts():
    """Get active alerts"""
    alerts = alert_vm.get_mock_alerts()
    return {"alerts": [a.model_dump() for a in alerts], "total": len(alerts)}


@router.get("/unread-count")
async def get_unread_count():
    alerts = alert_vm.get_mock_alerts()
    unread = sum(1 for a in alerts if not a.read)
    return {"unread": unread}


@router.post("/generate")
async def generate_alert(prediction: PredictionResult):
    """Generate alert from prediction result"""
    alert = alert_vm.generate_alert_from_prediction(prediction, student_name="Estudiante")
    if alert:
        return {"alert": alert.model_dump(), "generated": True}
    return {"generated": False, "reason": "Risk level too low"}


@router.put("/{alert_id}/read")
async def mark_as_read(alert_id: str):
    return {"id": alert_id, "read": True}
