"""
Core Configuration — Settings & Environment
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Sistema Nacional de Learning Analytics"
    DEBUG: bool = True

    # Firebase
    FIREBASE_PROJECT_ID: str = "prediccionriesgoacademico"
    FIREBASE_API_KEY: str = "AIzaSyDhug3B-1Kq6YseNYVmLRO8Qvk7P4tCkbU"
    FIREBASE_AUTH_DOMAIN: str = "prediccionriesgoacademico.firebaseapp.com"
    FIREBASE_STORAGE_BUCKET: str = "prediccionriesgoacademico.firebasestorage.app"
    FIREBASE_MESSAGING_SENDER_ID: str = "237142462692"
    FIREBASE_APP_ID: str = "1:237142462692:web:36b7708f8a9ded59bc1cf1"

    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "learning_analytics"

    # Risk thresholds
    RISK_LOW_THRESHOLD: float = 0.3
    RISK_MEDIUM_THRESHOLD: float = 0.6
    RISK_HIGH_THRESHOLD: float = 0.8

    class Config:
        env_file = ".env"


settings = Settings()
