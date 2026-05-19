"""
Firebase Firestore Database Connection
"""
import firebase_admin
from firebase_admin import credentials, firestore
from app.core.config import settings
import os

_firestore_client = None


def get_firestore_client():
    """Singleton Firestore client"""
    global _firestore_client
    if _firestore_client is None:
        if not firebase_admin._apps:
            # Use service account if available, otherwise use app config
            service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT", "")
            if service_account_path and os.path.exists(service_account_path):
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
            else:
                # Initialize with project ID for emulator / demo mode
                firebase_admin.initialize_app(options={
                    "projectId": settings.FIREBASE_PROJECT_ID,
                })
        _firestore_client = firestore.client()
    return _firestore_client


def get_db():
    return get_firestore_client()
