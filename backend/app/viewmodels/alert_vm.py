"""
Alert ViewModel — Manages alert generation and Firestore persistence
"""
from datetime import datetime
from typing import List, Optional
import uuid

from app.models.schemas import AlertOut, PredictionResult, RiskLevel


class AlertViewModel:
    """
    ViewModel for Alert Service — generates and manages academic alerts
    """

    ALERT_MESSAGES = {
        RiskLevel.MEDIUM: "El estudiante presenta indicadores de riesgo académico moderado. Se recomienda seguimiento.",
        RiskLevel.HIGH: "⚠️ El estudiante presenta alto riesgo académico. Se requiere intervención inmediata.",
        RiskLevel.CRITICAL: "🚨 ALERTA CRÍTICA: El estudiante está en riesgo inminente de deserción.",
    }

    def generate_alert_from_prediction(self, prediction: PredictionResult, student_name: str) -> Optional[AlertOut]:
        """Only generate alert if risk is medium or above"""
        if prediction.risk_level == RiskLevel.LOW:
            return None

        return AlertOut(
            id=str(uuid.uuid4()),
            student_id=prediction.student_id,
            student_name=student_name,
            institution_id=prediction.institution_id,
            risk_level=prediction.risk_level,
            message=self.ALERT_MESSAGES.get(prediction.risk_level, "Riesgo académico detectado."),
            factors=prediction.factors,
            read=False,
            created_at=datetime.utcnow()
        )

    def get_mock_alerts(self) -> List[AlertOut]:
        """Mock alerts for demo"""
        now = datetime.utcnow()
        return [
            AlertOut(id="a1", student_id="s001", student_name="Ana García", institution_id="UNAL",
                     risk_level=RiskLevel.CRITICAL, message="🚨 ALERTA CRÍTICA: Riesgo inminente de deserción.",
                     factors=["Promedio 2.8", "Asistencia 45%", "Sin entregas en 3 semanas"], read=False, created_at=now),
            AlertOut(id="a2", student_id="s002", student_name="Carlos Martínez", institution_id="UDEA",
                     risk_level=RiskLevel.HIGH, message="⚠️ Alto riesgo académico detectado.",
                     factors=["7 entregas tardías", "Login frecuencia baja"], read=False, created_at=now),
            AlertOut(id="a3", student_id="s003", student_name="María López", institution_id="UNAL",
                     risk_level=RiskLevel.MEDIUM, message="Riesgo moderado. Se recomienda seguimiento.",
                     factors=["Asistencia 68%", "Promedio 3.2"], read=True, created_at=now),
            AlertOut(id="a4", student_id="s004", student_name="José Rodríguez", institution_id="ITBA",
                     risk_level=RiskLevel.HIGH, message="⚠️ Disminución significativa en actividad académica.",
                     factors=["Sin acceso en 10 días", "Entregas tardías"], read=False, created_at=now),
            AlertOut(id="a5", student_id="s005", student_name="Laura Sánchez", institution_id="UDISTRITAL",
                     risk_level=RiskLevel.MEDIUM, message="Indicadores de riesgo moderado detectados.",
                     factors=["Baja participación en foros", "Tiempo de conexión reducido"], read=False, created_at=now),
        ]


alert_vm = AlertViewModel()
