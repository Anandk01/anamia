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

__all__ = [
    'auth_bp',
    'predict_bp',
    'reports_bp',
    'alerts_bp',
    'admin_bp',
    'retrain_bp',
    'ocr_bp',
    'chat_bp',
]
