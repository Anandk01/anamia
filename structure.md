
Anemia Detection System - Project Structure Summary
📋 Project Overview
A full-stack ML-powered medical diagnostic system for anemia risk assessment, featuring multi-model architecture, role-based access control, OCR capabilities, and real-time chatbot assistance.

🏗️ Architecture
Tech Stack
Backend: Flask (Python 3.10+)

Frontend: React 19 + Vite + Tailwind CSS v4

Database: SQLite (anemia.db)

ML Models: scikit-learn (K-Means, Random Forest, Gradient Boosting)

AI Services: Google Gemini API (chatbot, report generation)

Testing: pytest (backend), vitest + React Testing Library (frontend)

📁 Backend Structure (/backend)
Core Application
app.py                    # Main Flask application entry point
db.py                     # Database initialization and schema
conftest.py               # pytest configuration and fixtures
requirements.txt          # Python dependencies (30 packages)
anemia.db                 # SQLite database (users, predictions, alerts, chat history)
.env / .env.example       # Environment variables (API keys, secrets)

Copy

Insert at cursor
Blueprints (Modular Routes)
blueprints/
├── auth_bp.py            # Login, register, password reset, JWT tokens
├── predict_bp.py         # /predict (K-Means), /triage (Random Forest)
├── reports_bp.py         # /reports (historical predictions), /patient-history
├── admin_bp.py           # User management, system stats
├── alerts_bp.py          # Alert creation, retrieval, dismissal
├── chat_bp.py            # Chatbot conversation endpoint
├── ocr_bp.py             # PDF/image upload → OCR → CBC extraction
└── retrain_bp.py         # Model retraining with new data


Copy

Insert at cursor
Services (Business Logic)
services/
├── prediction_service.py         # K-Means clustering, severity classification
├── type_classifier.py            # Anemia type detection (Iron-deficiency, B12, etc.)
├── recommendation_service.py     # Personalized diet/lifestyle recommendations
├── explainability.py             # SHAP-based model explanations
├── chatbot_service.py            # Rule-based chatbot fallback
├── gemini_chatbot_service.py     # Google Gemini AI chatbot
├── gemini_report_service.py      # AI-generated medical reports
├── ocr_service.py                # Tesseract OCR + PDF processing
├── alert_service.py              # Alert logic and thresholds
└── rag_knowledge.py              # RAG knowledge base for chatbot


Copy

Insert at cursor
Middleware
middleware/
├── auth.py               # JWT token verification decorator
└── rbac.py               # Role-based access control (admin/doctor/patient)

Copy

Insert at cursor
ML Models
models/
├── kmeans_model.pkl              # Unsupervised clustering (3 risk groups)
├── scaler.pkl                    # StandardScaler for K-Means
├── risk_mapping.pkl              # Cluster → Risk label mapping
├── triage_rf_model.pkl           # Random Forest (symptom → test needed?)
├── rf_anemia_classifier.pkl      # Supervised anemia type classifier
├── rf_scaler.pkl                 # Scaler for supervised model
├── gb_severity_classifier.pkl    # Gradient Boosting (severity levels)
├── backup/                       # Model version backups
└── new/                          # Retrained model staging area


Copy

Insert at cursor
Training Scripts
train.py                  # K-Means clustering training
train_triage.py           # Random Forest triage model training
train_supervised.py       # Supervised classifiers training
syntheticdata.py          # Synthetic dataset generator

Copy

Insert at cursor
Tests (Property-Based + Unit)
tests/
├── test_smoke.py                 # Basic health checks
├── test_predict_unit.py          # Unit tests for prediction logic
├── 
test_predict_properties.py    # Property-based tests (Hypothesis)
├── test_auth_properties.py       # Auth flow property tests
├── test_rbac_properties.py       # RBAC permission tests
├── test_ocr_properties.py        # OCR extraction tests
├── test_alerts_properties.py     # Alert system tests
├── test_reports_properties.py    # Report generation tests
├── test_retrain_properties.py    # Model retraining tests
├── test_recommendations.py       # Recommendation engine tests
└── test_type_classifier.py       # Anemia type classifier tests


Copy

Insert at cursor
📁 Frontend Structure (/frontend)
Pages (Role-Based Dashboards)
pages/
├── LoginPage.jsx         # Login form with JWT authentication
├── RegisterPage.jsx      # User registration
├── ForgotPasswordPage.jsx # Password reset flow
├── DoctorDashboard.jsx   # Doctor view (CBC form, triage, reports)
├── PatientDashboard.jsx  # Patient view (history, trends, chatbot)
└── AdminDashboard.jsx    # Admin panel (user management, retraining)

Copy

Insert at cursor
Components (Reusable UI)
components/
├── CBCForm.jsx           # 8-field CBC input form
├── PredictionResult.jsx  # Risk category display with color coding
├── ReportHistory.jsx     # Historical predictions table
├── PatientTriage.jsx     # Multi-step symptom interview (Random Forest)
├── Chatbot.jsx           # AI chatbot interface (Gemini API)
├── HbTrendChart.jsx      # Hemoglobin trend visualization (Recharts)
├── DietRecommendations.jsx # Personalized diet suggestions
├── HealthTips.jsx        # Educational content cards
├── AlertLog.jsx          # Alert notifications panel
├── RetrainingPanel.jsx   # CSV upload for model retraining
├── PDFDownloadButton.jsx # Generate PDF reports (jsPDF)
└── LanguageSelector.jsx  # i18n language switcher


Copy

Insert at cursor
Internationalization (i18n)
i18n/
├── en.json               # English translations
├── hi.json               # Hindi translations
├── ta.json               # Tamil translations
└── kn.json               # Kannada translations

Copy

Insert at cursor
🗄️ Database Schema (SQLite)
user
├── user_id (PK)
├── username (UNIQUE)
├── password (bcrypt hashed)
├── email
├── role (admin | doctor | patient)
└── created_at

prediction
├── patient_id (PK)
├── username (FK → user)
├── rbc, mcv, mch, mchc, rdw, tlc, plt, hgb (REAL)
├── risk_category (Low | Moderate | High)
├── severity (Mild | Moderate | Severe)
├── anemia_type (Iron-deficiency | B12 | Thalassemia | etc.)
└── date (TIMESTAMP)

alert
├── alert_id (PK)
├── username (FK → user)
├── message (TEXT)
├── severity (info | warning | critical)
├── dismissed (BOOLEAN)
└── created_at

chat_history
├── chat_id (PK)
├── username (FK → user)
├── message (TEXT)
├── response (TEXT)
└── timestamp


Copy

Insert at cursor
🤖 Machine Learning Models
1. K-Means Clustering (Unsupervised)
Purpose: Segment patients into 3 risk groups

Features: RBC, MCV, MCH, MCHC, RDW, TLC, PLT, HGB (8 features)

Output: Low/Moderate/High Risk

Files: kmeans_model.pkl, scaler.pkl, risk_mapping.pkl

2. Random Forest Triage (Supervised)
Purpose: Predict if CBC test is needed based on symptoms

Features: Age, Sex, Family_History_Anemia, Vegan_Diet, Fatigue, Dizziness, Breathlessness, Paleness

Output: Binary (Test needed: Yes/No)

Accuracy: 100% on synthetic test set

Files: triage_rf_model.pkl

3. Random Forest Anemia Classifier
Purpose: Classify anemia type

Output: Iron-deficiency, B12, Thalassemia, etc.

Files: rf_anemia_classifier.pkl, rf_scaler.pkl

4. Gradient Boosting Severity Classifier
Purpose: Predict severity level

Output: Mild, Moderate, Severe

Files: gb_severity_classifier.pkl

🚀 Key Features
Multi-Model Prediction Pipeline - K-Means + Gradient Boosting + Random Forest + SHAP explainability

Patient Triage System - 8-question interview, one-at-a-time UI

OCR Integration - Upload PDF/image → extract CBC values

AI Chatbot - Google Gemini with RAG knowledge base

Personalized Recommendations - Diet/lifestyle based on anemia type

Alert System - Critical HGB threshold notifications

Model Retraining - Admin can upload new data and retrain

Multilingual Support - English, Hindi, Tamil, Kannada

PDF Report Generation - Patient history with trend charts

Hemoglobin Trend Visualization - Interactive line charts

🔐 Authentication & Authorization
JWT-Based Auth
Login → JWT token (24hr expiry)

Token stored in localStorage

@token_required decorator validates requests

RBAC Roles
Admin: User management, model retraining, system stats

Doctor: CBC prediction, triage, view all reports

Patient: View own history, chatbot, download PDFs

📊 Project Metrics
Total Files: ~120

Backend LOC: ~8,000 (Python)

Frontend LOC: ~6,000 (JSX/JS)

ML Models: 4 trained models

API Endpoints: 25+

UI Components: 15 reusable components

Test Cases: 70+ total

Languages Supported: 4

🎯 College Project Highlights
ML Techniques
Unsupervised Learning (K-Means)

Supervised Learning (Random Forest, Gradient Boosting)

Feature Engineering (StandardScaler)

Model Explainability (SHAP)

Software Engineering
Modular Architecture (Blueprints, Services, Middleware)

RESTful API Design

JWT Authentication + RBAC

Property-Based Testing (Hypothesis)

Internationalization (i18next