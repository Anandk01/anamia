"""
Flask Blueprints package for the Anemia Detection and Management System.

Exports all blueprint objects so they can be registered with the Flask app.
"""

from .auth_bp import auth_bp
from .predict_bp import predict_bp
from .reports_bp import reports_bp
from .alerts_bp import alerts_bp
from .admin_bp import admin_bp
from .retrain_bp import retrain_bp
from .ocr_bp import ocr_bp
from .chat_bp import chat_bp
from .appointments_bp import appointments_bp
from .medication_bp import medication_bp
from .forum_bp import forum_bp
from .education_bp import education_bp
from .notifications_bp import notifications_bp
from .prescriptions_bp import prescriptions_bp
from .analytics_bp import analytics_bp
from .profile_bp import profile_bp

__all__ = [
    'auth_bp',
    'predict_bp',
    'reports_bp',
    'alerts_bp',
    'admin_bp',
    'retrain_bp',
    'ocr_bp',
    'chat_bp',
    'appointments_bp',
    'medication_bp',
    'forum_bp',
    'education_bp',
    'notifications_bp',
    'prescriptions_bp',
    'analytics_bp',
    'profile_bp',
]
