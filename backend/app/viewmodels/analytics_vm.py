"""
Analytics Service — IA Predictiva, Clustering, Risk Detection
Uses Scikit-Learn: Logistic Regression + Random Forest
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from typing import List, Dict, Tuple
from datetime import datetime
import random

from app.models.schemas import PredictionResult, RiskLevel, StudentProfile
from app.core.config import settings


class AnalyticsViewModel:
    """
    ViewModel for Analytics — bridges ML models with API layer
    MVVM: this is the ViewModel layer for analytics
    """

    def __init__(self):
        self.scaler = StandardScaler()
        self.rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.lr_model = LogisticRegression(random_state=42)
        self.kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
        self._trained = False
        self._bootstrap_models()

    def _bootstrap_models(self):
        """Synthetic training data to bootstrap models (replace with real data)"""
        np.random.seed(42)
        n = 500
        X = np.column_stack([
            np.random.uniform(0, 10, n),      # avg_score
            np.random.uniform(0, 1, n),        # attendance_rate
            np.random.randint(0, 20, n),       # late_submissions
            np.random.uniform(0, 7, n),        # login_frequency per week
            np.random.uniform(0, 100, n),      # total_submissions
            np.random.uniform(0, 5, n),        # connection_hours per day
        ])
        # Risk label: high scores + attendance = low risk
        risk_score = (1 - X[:, 0] / 10) * 0.4 + (1 - X[:, 1]) * 0.3 + (X[:, 2] / 20) * 0.3
        y = (risk_score > 0.5).astype(int)

        X_scaled = self.scaler.fit_transform(X)
        self.rf_model.fit(X_scaled, y)
        self.lr_model.fit(X_scaled, y)
        self.kmeans.fit(X_scaled)
        self._trained = True

    def _features_from_profile(self, profile: StudentProfile) -> np.ndarray:
        return np.array([[
            profile.avg_score,
            profile.attendance_rate,
            profile.late_submissions,
            profile.login_frequency,
            profile.submissions_on_time + profile.late_submissions,
            random.uniform(1, 6),  # Placeholder: connection hours
        ]])

    def _risk_level(self, score: float) -> RiskLevel:
        if score >= settings.RISK_HIGH_THRESHOLD:
            return RiskLevel.CRITICAL
        elif score >= settings.RISK_MEDIUM_THRESHOLD:
            return RiskLevel.HIGH
        elif score >= settings.RISK_LOW_THRESHOLD:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _risk_factors(self, profile: StudentProfile, score: float) -> List[str]:
        factors = []
        if profile.avg_score < 4.0:
            factors.append("Promedio de notas por debajo del mínimo")
        if profile.attendance_rate < 0.7:
            factors.append("Asistencia inferior al 70%")
        if profile.late_submissions > 3:
            factors.append("Múltiples entregas tardías")
        if profile.login_frequency < 2:
            factors.append("Baja frecuencia de acceso a la plataforma")
        if not factors:
            factors.append("Comportamiento académico estable")
        return factors

    def predict_student_risk(self, profile: StudentProfile) -> PredictionResult:
        X = self._features_from_profile(profile)
        X_scaled = self.scaler.transform(X)

        rf_prob = self.rf_model.predict_proba(X_scaled)[0][1]
        lr_prob = self.lr_model.predict_proba(X_scaled)[0][1]
        risk_score = (rf_prob * 0.6 + lr_prob * 0.4)  # Weighted ensemble
        cluster_id = int(self.kmeans.predict(X_scaled)[0])

        return PredictionResult(
            student_id=profile.student_id,
            institution_id=profile.institution_id,
            risk_score=round(risk_score, 4),
            risk_level=self._risk_level(risk_score),
            dropout_probability=round(risk_score * 0.85, 4),
            factors=self._risk_factors(profile, risk_score),
            cluster_id=cluster_id,
            predicted_at=datetime.utcnow()
        )

    def batch_predict(self, profiles: List[StudentProfile]) -> List[PredictionResult]:
        return [self.predict_student_risk(p) for p in profiles]

    def get_cluster_summary(self) -> Dict:
        cluster_names = {
            0: "Alto rendimiento",
            1: "Riesgo moderado",
            2: "En riesgo",
            3: "Crítico / Deserción inminente"
        }
        return {str(k): v for k, v in cluster_names.items()}

    def generate_mock_stats(self) -> Dict:
        """Generate realistic mock analytics for dashboard demo"""
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
                {"course": "Cálculo I", "risk_rate": 0.34},
                {"course": "Programación I", "risk_rate": 0.28},
                {"course": "Álgebra Lineal", "risk_rate": 0.25},
                {"course": "IA Fundamentos", "risk_rate": 0.22},
                {"course": "Estadística", "risk_rate": 0.19},
            ],
            "cluster_distribution": [
                {"cluster": "Alto rendimiento", "count": 4200, "pct": 33.7},
                {"cluster": "Riesgo moderado", "count": 3860, "pct": 31.0},
                {"cluster": "En riesgo", "count": 2890, "pct": 23.2},
                {"cluster": "Crítico", "count": 1500, "pct": 12.1},
            ]
        }


# Singleton
analytics_vm = AnalyticsViewModel()
