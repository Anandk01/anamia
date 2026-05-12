# Design Document: Anemia Detection and Management System

## Overview

The Anemia Detection and Management System (ADMS) is a full-stack clinical decision-support platform. This design replaces the original unsupervised K-Means clustering approach with a **supervised multi-output ML pipeline** using clinically grounded ground-truth labels derived from WHO/clinical HGB thresholds. The frontend is a completely new **desktop-application-style UI** (dark sidebar, dense data panels, Linear/VS Code aesthetic).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              React + Vite Frontend (Desktop App UI)             │
│  Inter font · Indigo accent · Dark sidebar · Dense panels       │
│  react-router-dom · i18next · axios · Recharts · jsPDF          │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/JSON (JWT Bearer)
┌────────────────────────────▼────────────────────────────────────┐
│                     Flask REST API (Python)                     │
│  Blueprints: auth, predict, reports, alerts, admin, retrain     │
│  Middleware: JWT validation · RBAC · audit logging              │
└──────┬──────────────┬──────────────┬──────────────┬────────────┘
       │              │              │              │
┌──────▼──────┐ ┌─────▼──────┐ ┌────▼────┐ ┌──────▼──────┐
│  SQLite DB  │ │  New ML     │ │  SMTP   │ │  OCR Engine │
│  anemia.db  │ │  Pipeline   │ │ (Gmail) │ │ (Tesseract) │
│  6 tables   │ │  RF + GB    │ │         │ │             │
└─────────────┘ └────────────┘ └─────────┘ └─────────────┘
```

---

## New ML Pipeline — Core Design Decision

### Why Replace K-Means?

The original K-Means approach was **unsupervised** — it grouped patients by CBC similarity with no ground truth. The cluster-to-risk mapping was post-hoc (based on mean HGB per cluster), making it unreliable and non-reproducible across different datasets.

### New Supervised Pipeline

```
CBC Input (8 features)
    │
    ▼
StandardScaler (fit on training data)
    │
    ├──► Random Forest Classifier (binary)
    │       Features: all 8 CBC fields
    │       Target: anemia_detected (0/1)
    │       Labels derived from: HGB < 12.0 (female) or < 13.0 (male) → 1
    │       Output: anemia_detected + predict_proba confidence
    │
    ├──► Gradient Boosting Classifier (multi-class, only if anemia_detected=1)
    │       Features: all 8 CBC fields
    │       Target: severity_label (0=None, 1=Mild, 2=Moderate, 3=Severe)
    │       Labels derived from WHO HGB thresholds:
    │         HGB ≥ 12.0 → None
    │         10.0 ≤ HGB < 12.0 → Mild
    │         8.0 ≤ HGB < 10.0 → Moderate
    │         HGB < 8.0 → Severe
    │       Output: severity_level + predict_proba confidence
    │
    ├──► Clinical Rule Engine (Type Classification)
    │       Input: MCV, MCH, MCHC, RDW
    │       Rules (clinically validated):
    │         MCV < 80 AND MCH < 27 → Iron-Deficiency (microcytic hypochromic)
    │         MCV > 100 → Macrocytic:
    │           RDW > 14.5 → Folate Deficiency
    │           RDW ≤ 14.5 → Vitamin B12 Deficiency
    │         MCV 80–100 → Other (normocytic)
    │       Confidence: distance from threshold boundaries (0.0–1.0)
    │
    ├──► SHAP Explainability (TreeExplainer on RF model)
    │       Compute SHAP values for the prediction
    │       Extract top-3 features by |SHAP value|
    │       Map to directional labels using population reference ranges:
    │         HGB: Low < 12, Normal 12–17, High > 17
    │         MCV: Low < 80, Normal 80–100, High > 100
    │         MCH: Low < 27, Normal 27–33, High > 33
    │         MCHC: Low < 32, Normal 32–36, High > 36
    │         RDW: Normal < 14.5, Elevated ≥ 14.5
    │         RBC: Low < 4.0, Normal 4.0–5.5, High > 5.5
    │         TLC: Low < 4.0, Normal 4.0–11.0, High > 11.0
    │         PLT: Low < 150, Normal 150–400, High > 400
    │
    ├──► Recommendation Engine
    │       Diet lookup by anemia_type (≥5 items + rationale each)
    │       Health tips by (severity, type, age, sex)
    │       Vegan filter using item tags
    │
    ├──► Alert Service (if HGB < 7.0 or severity == "Severe")
    │       Email doctor with patient details
    │       Retry up to 3× at 30s intervals
    │
    └──► DB Persistence → prediction table
```

### Training Data Labelling Strategy

The existing CBC dataset (`CBC data_for_meandeley_csv.csv`) has no anemia labels. We derive ground-truth labels from HGB values using WHO clinical thresholds:

```python
# Anemia detection label
df['anemia_detected'] = (df['HGB'] < 12.0).astype(int)  # simplified threshold

# Severity label (only meaningful when anemia_detected=1)
def severity_label(hgb):
    if hgb >= 12.0: return 0  # None
    elif hgb >= 10.0: return 1  # Mild
    elif hgb >= 8.0: return 2   # Moderate
    else: return 3              # Severe
```

This is clinically valid because HGB is the gold-standard diagnostic criterion for anemia per WHO guidelines.

---

## Frontend Design System

### Visual Language

| Property | Value |
|---|---|
| Sidebar background | `#0f1117` |
| Content background | `#f8f9fa` |
| Panel background | `#ffffff` |
| Accent colour | `#6366f1` (indigo-500) |
| Success | `#10b981` (emerald-500) |
| Warning | `#f59e0b` (amber-500) |
| Danger | `#ef4444` (red-500) |
| Font | Inter (system fallback: -apple-system) |
| Border radius | `6px` (panels), `4px` (inputs), `999px` (badges) |
| Transition | `150ms ease` |
| Table row height | `36px` (compact) |
| Sidebar width | `220px` (fixed) |

### Layout Pattern

```
┌──────────────────────────────────────────────────────┐
│  220px dark sidebar  │  Header bar (48px)            │
│  ─────────────────── │  ─────────────────────────── │
│  Nav items           │                               │
│  (icon + label)      │  Content area                 │
│                      │  (internal scroll)            │
│  ─────────────────── │                               │
│  User avatar + name  │                               │
│  Language selector   │                               │
└──────────────────────────────────────────────────────┘
```

No full-page scrolling. All content panels scroll internally. Fixed viewport.

### Component Density

- Table rows: `py-1.5 px-3`, `text-sm`
- Form inputs: `py-1.5 px-2.5`, `text-sm`, `border border-slate-200`
- Buttons: `py-1.5 px-3`, `text-sm`, `font-medium`
- Section headers: `text-xs font-semibold uppercase tracking-wide text-slate-500`
- No large hero sections, no card stacks, no centered layouts for data views

---

## Components and Interfaces

### Backend Blueprints

| Blueprint | Prefix | Key Routes |
|---|---|---|
| auth_bp | `/auth` | POST /register, /verify-register-otp, /login, /logout, /forgot-password, /verify-reset-otp |
| predict_bp | `/api` | POST /predict, GET /reports, GET /reports/<id>, GET /trend/<username> |
| alerts_bp | `/api/alerts` | GET /, POST /test |
| admin_bp | `/api` | GET /stats, GET /users, POST /users, PATCH /users/<id>/deactivate |
| retrain_bp | `/api/retrain` | POST /upload, /start, /approve, /rollback, GET /status |
| ocr_bp | `/api/ocr` | POST /upload |
| chat_bp | `/api/chat` | POST /message |

### Frontend Page Structure

```
src/
├── App.jsx                        (router + PrivateRoute)
├── pages/
│   ├── LoginPage.jsx              (split dark/light layout)
│   ├── RegisterPage.jsx           (2-step OTP flow)
│   ├── ForgotPasswordPage.jsx     (3-step flow)
│   ├── PatientDashboard.jsx       (sidebar + content)
│   ├── DoctorDashboard.jsx        (sidebar + content)
│   └── AdminDashboard.jsx         (sidebar + content)
├── components/
│   ├── CBCForm.jsx                (compact 2-col grid)
│   ├── PredictionResult.jsx       (status bar + SHAP table)
│   ├── DietRecommendations.jsx    (collapsible list)
│   ├── HealthTips.jsx             (numbered list)
│   ├── ReportHistory.jsx          (dense table + drawer)
│   ├── HbTrendChart.jsx           (Recharts ComposedChart)
│   ├── PDFDownloadButton.jsx      (icon button + toast)
│   ├── LanguageSelector.jsx       (compact dropdown)
│   ├── Chatbot.jsx                (floating panel)
│   ├── AlertLog.jsx               (dense table)
│   └── RetrainingPanel.jsx        (dropzone + metrics)
├── hooks/
│   ├── useAuth.js
│   └── useTranslation.js
├── api/
│   └── client.js                  (axios + interceptors)
├── services/
│   └── pdfService.js
└── i18n/
    ├── en.json
    ├── hi.json
    └── ta.json
```

---

## Data Models

### Extended SQLite Schema

```sql
CREATE TABLE IF NOT EXISTS user (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'patient',
    status        TEXT    NOT NULL DEFAULT 'active',
    language_pref TEXT    NOT NULL DEFAULT 'en',
    vegan_diet    INTEGER NOT NULL DEFAULT 0,
    age           INTEGER,
    sex           INTEGER,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until  TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prediction (
    prediction_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT    NOT NULL,
    rbc             REAL    NOT NULL,
    mcv             REAL    NOT NULL,
    mch             REAL    NOT NULL,
    mchc            REAL    NOT NULL,
    rdw             REAL    NOT NULL,
    tlc             REAL    NOT NULL,
    plt             REAL    NOT NULL,
    hgb             REAL    NOT NULL,
    anemia_detected INTEGER NOT NULL,
    severity_level  TEXT    NOT NULL,
    anemia_type     TEXT    NOT NULL,
    confidence      REAL,
    explanation     TEXT,   -- JSON array of SHAP top-3
    diet_recs       TEXT,   -- JSON array
    health_tips     TEXT,   -- JSON array
    risk_category   TEXT    NOT NULL DEFAULT 'N/A',
    date            TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS alert_log (
    alert_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id   INTEGER NOT NULL,
    recipient_email TEXT    NOT NULL,
    recipient_username TEXT NOT NULL,
    patient_username TEXT   NOT NULL,
    hgb_value       REAL    NOT NULL,
    severity_level  TEXT    NOT NULL,
    sent_at         TEXT    NOT NULL,
    delivery_status TEXT    NOT NULL DEFAULT 'pending',
    retry_count     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS jwt_blacklist (
    jti     TEXT PRIMARY KEY,
    exp     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS access_violation_log (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT    NOT NULL,
    endpoint    TEXT    NOT NULL,
    role_claim  TEXT    NOT NULL,
    timestamp   TEXT    NOT NULL,
    ip_address  TEXT,
    action      TEXT
);

CREATE TABLE IF NOT EXISTS retrain_log (
    retrain_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_username  TEXT    NOT NULL,
    dataset_size    INTEGER NOT NULL,
    accuracy        REAL,
    precision_score REAL,
    recall          REAL,
    f1_score        REAL,
    status          TEXT    NOT NULL,
    triggered_at    TEXT    NOT NULL,
    completed_at    TEXT
);
```

---

## Correctness Properties

*(Unchanged from requirements — all 22 properties apply. Key changes: Property 1 now validates RF output, Property 2 validates GB severity against HGB thresholds, Property 4 validates SHAP top-3 output.)*

---

## Error Handling

All API errors return:
```json
{
  "status": "error",
  "code": "ERROR_CODE",
  "message": "Human-readable description",
  "details": {}
}
```

---

## Testing Strategy

- **Backend**: `pytest` + `hypothesis` for property-based tests; `pytest-cov` for coverage (≥80%)
- **ML**: Unit tests for type_classifier rule boundaries; integration test for full prediction pipeline
- **Frontend**: Vitest + React Testing Library for component tests
- **Property tests**: minimum 100 iterations per property
- **SHAP**: mock `shap.TreeExplainer` in tests to avoid model dependency
