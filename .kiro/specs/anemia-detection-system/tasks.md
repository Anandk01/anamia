# Implementation Tasks: Anemia Detection and Management System

## Task Overview

Complete rebuild with a new supervised ML pipeline (Random Forest + Gradient Boosting + clinical rule engine) replacing the old unsupervised K-Means approach. The frontend is a fully new desktop-application-style UI (dark sidebar, dense panels, Linear/VS Code aesthetic). Tasks are ordered by dependency: ML training first, then backend foundation, auth, prediction pipeline, supporting services, frontend, testing.

---

## Phase 0: New ML Training Pipeline

- [x] 0. Train new supervised ML models to replace K-Means
  - [x] 0.1 Write `backend/train_supervised.py` — label the CBC dataset using HGB clinical thresholds: anemia_detected (HGB < 12.0 for females / < 13.0 for males → 1, else 0); severity_label (None/Mild/Moderate/Severe per WHO thresholds); split 80/20 train/test
  - [x] 0.2 Train Random Forest binary classifier for anemia detection — features: all 8 CBC fields (RBC, MCV, MCH, MCHC, RDW, TLC, PLT, HGB); save as `backend/models/rf_anemia_classifier.pkl` and `backend/models/rf_scaler.pkl`; print accuracy, precision, recall, F1
  - [x] 0.3 Train Gradient Boosting multi-class classifier for severity — features: all 8 CBC fields; target: severity_label (0=None, 1=Mild, 2=Moderate, 3=Severe); save as `backend/models/gb_severity_classifier.pkl`; print classification report
  - [x] 0.4 Write `backend/services/type_classifier.py` — clinical rule engine for anemia type using MCV/MCH/MCHC/RDW patterns: MCV < 80 + MCH < 27 → Iron-Deficiency (microcytic); MCV > 100 → B12/Folate Deficiency (macrocytic, use RDW to differentiate: RDW > 14.5 → Folate, else B12); MCV 80–100 → Other (normocytic); return type + confidence score (0.0–1.0) based on how far values deviate from thresholds
  - [x] 0.5 Write `backend/services/explainability.py` — SHAP-based feature importance using `shap.TreeExplainer` on the RF classifier; for each prediction return top-3 features with SHAP values and directional labels (Low/High/Normal/Elevated) based on population reference ranges; fallback to permutation importance if SHAP fails
  - [x] 0.6 Add `shap`, `PyJWT==2.8.0`, `bcrypt==4.1.2`, `hypothesis==6.100.0`, `pytest==7.4.0`, `pytest-cov==4.1.0`, `pytesseract==0.3.10`, `pdf2image==1.17.0`, `Pillow==10.3.0` to `backend/requirements.txt` with pinned versions

---

## Phase 1: Foundation

- [x] 1. Initialise project structure and database schema
  - [x] 1.1 Create `backend/blueprints/` directory with skeleton Blueprint files: `auth_bp.py`, `predict_bp.py`, `reports_bp.py`, `alerts_bp.py`, `admin_bp.py`, `retrain_bp.py`, `ocr_bp.py`, `chat_bp.py` — each file defines a Flask Blueprint with the correct url_prefix and a placeholder index route
  - [x] 1.2 Rewrite `backend/app.py` — clean factory function `create_app()`, register all 8 Blueprints, load new ML models (rf_anemia_classifier, gb_severity_classifier) at startup, remove all old inline route definitions, keep CORS and dotenv setup
  - [x] 1.3 Write `backend/db.py` — `get_db()` and `init_db()` creating all tables: `user` (user_id, username, email, password_hash, role, status, language_pref, vegan_diet, age, sex, failed_attempts, locked_until, created_at), `prediction` (prediction_id, username, rbc, mcv, mch, mchc, rdw, tlc, plt, hgb, anemia_detected, severity_level, anemia_type, confidence, explanation JSON, diet_recs JSON, health_tips JSON, risk_category, date), `alert_log`, `jwt_blacklist`, `access_violation_log`, `retrain_log`; seed default admin/doctor accounts with bcrypt-hashed passwords
  - [x] 1.4 Add `GET /health` endpoint in `app.py` — return `{"status": "ok", "models": {"rf_classifier": true/false, "gb_severity": true/false}, "db": true/false}`
  - [x] 1.5 Create `backend/models/` directory; move/copy existing `.pkl` files there; update all load paths in app.py

---

## Phase 2: Authentication and RBAC

- [x] 2. Implement authentication system
  - [x] 2.1 Implement `POST /auth/register` in `auth_bp.py` — validate unique username/email, password ≥ 8 chars, generate 6-digit OTP via `secrets.randbelow`, send via SMTP using existing email config, store OTP hash + expiry in memory dict with 10-minute TTL
  - [x] 2.2 Implement `POST /auth/verify-register-otp` — validate OTP against stored hash, create user with `role="patient"`, `status="active"`, bcrypt hash cost=12, issue JWT (PyJWT, 24h expiry, jti=uuid4, role claim), return `{"token": "...", "user": {...}}`
  - [x] 2.3 Implement `POST /auth/login` — lookup by username or email, verify bcrypt hash, check `status="active"`, check `locked_until`, issue JWT on success, reset `failed_attempts` to 0
  - [x] 2.4 Implement account lockout — on bad password: increment `failed_attempts`, if ≥ 5 within 15 min set `locked_until = now + 15min`, send lockout email; on login check `locked_until > now` → return 401 with unlock time
  - [x] 2.5 Implement `POST /auth/logout` — require valid JWT, insert `jti` into `jwt_blacklist` with `exp` timestamp
  - [x] 2.6 Implement `POST /auth/forgot-password` and `POST /auth/verify-reset-otp` — same OTP flow, on success update `password_hash` with new bcrypt hash
  - [x] 2.7 Write `backend/middleware/auth.py` — `require_auth` decorator: decode JWT with PyJWT, check expiry, check `jwt_blacklist` table, attach `g.current_user` dict to Flask request context; return 401 on any failure
  - [x] 2.8 Write `backend/middleware/rbac.py` — `require_role(*roles)` decorator: read `g.current_user["role"]`, if not in allowed roles insert row into `access_violation_log` and return `{"error": "Insufficient permissions"}` 403

- [x] 3. Write property-based tests for auth and RBAC
  - [x] 3.1 `backend/tests/test_auth_properties.py` — use `hypothesis` strategies: Property 14 (any valid registration input → account has role=patient), Property 15 (wrong/expired OTP → 400, no account created), Property 16 (successful login JWT exp within ±60s of now+24h), Property 17 (after logout, same token → 401)
  - [x] 3.2 `backend/tests/test_rbac_properties.py` — Property 13: parametrize all forbidden (role, endpoint, method) combos from permission matrix; for each assert 403 and business logic not executed

---

## Phase 3: New Supervised Prediction Pipeline

- [x] 4. Implement CBC prediction pipeline with new ML models
  - [x] 4.1 Write `backend/schemas/cbc_schema.py` — `validate_cbc(data)` function: normalise field names to lowercase, check all 8 fields present and numeric (float/int), check values ≥ 0; return `(normalised_dict, errors_list)`
  - [x] 4.2 Write `backend/services/prediction_service.py` — `PredictionService` class: load `rf_anemia_classifier.pkl`, `rf_scaler.pkl`, `gb_severity_classifier.pkl` at init; `predict(cbc_dict)` method: scale input → RF binary prediction (anemia_detected 0/1) → if anemia_detected=1 run GB severity classifier → return structured result dict; include model confidence scores from `predict_proba`
  - [x] 4.3 Integrate `type_classifier.py` into prediction pipeline — call after severity; pass MCV, MCH, MCHC, RDW values; return `anemia_type` string + `confidence` float
  - [x] 4.4 Integrate `explainability.py` into prediction pipeline — call SHAP TreeExplainer on RF model with the input vector; extract top-3 feature names + SHAP values + directional labels; return as list of `{"feature": str, "direction": str, "shap_value": float}`
  - [x] 4.5 Implement `POST /api/predict` in `predict_bp.py` — validate CBC schema, run full pipeline (PredictionService → type_classifier → explainability → recommendation_service → alert_service → persist to DB), return full JSON result; enforce `require_auth` + `require_role("patient", "doctor")`
  - [x] 4.6 Implement `GET /api/reports` — paginated 20/page, role-filtered (patient/doctor see own records, admin sees all); `GET /api/reports/<id>` with ownership check; return full prediction detail including explanation and recommendations
  - [x] 4.7 Implement `GET /api/trend/<username>` — return last 12+ HGB values with dates and severity_level for trend chart; enforce ownership

- [x] 5. Write property-based tests for new prediction pipeline
  - [x] 5.1 `backend/tests/test_predict_properties.py` — Property 1 (RF output is always 0 or 1), Property 2 (GB severity always matches HGB threshold rules), Property 3 (confidence always in [0.0, 1.0]), Property 4 (SHAP explanation always has exactly 3 entries with feature name + direction)
  - [x] 5.2 `backend/tests/test_predict_properties.py` — Property 9 (DB round-trip: stored CBC values match input to 6dp), Property 11 (invalid schema → 400, PredictionService.predict never called)
  - [x] 5.3 `backend/tests/test_predict_properties.py` — Property 10 (CBC JSON serialisation round-trip to 6dp), Property 18 (pagination: ≤20/page, union = N total, no duplicates)
  - [x] 5.4 `backend/tests/test_predict_unit.py` — example-based: happy path with known CBC values, missing field, non-numeric field, HGB boundary values (7.99, 8.0, 9.99, 10.0, 11.9, 12.0), verify RF and GB outputs match expected labels

---

## Phase 4: Recommendations and Alerts

- [x] 6. Implement Recommendation Engine
  - [x] 6.1 Write `backend/services/recommendation_service.py` — `get_diet_recommendations(anemia_type, vegan=False)`: lookup table with ≥5 food items per type (Iron-Deficiency: spinach, lentils, red meat, tofu, pumpkin seeds + rationale each; B12: eggs, dairy, salmon, fortified cereals, beef; Folate: broccoli, asparagus, avocado, chickpeas, oranges; Other/N/A: balanced iron-maintenance list); apply vegan filter using `is_vegan` tag on each item
  - [x] 6.2 Write `get_health_tips(severity_level, anemia_type, age=None, sex=None)` — ≥3 tips per (severity, type) combination; if age < 18 add paediatric tip; if sex=1 (female) add menstrual iron-loss tip; return list of tip strings
  - [x] 6.3 Write `backend/tests/test_recommendations.py` — Property 5 (≥5 food items for any anemia_type input), Property 6 (vegan=True result is strict subset of vegan=False result, no non-vegan items in vegan result)

- [x] 7. Implement Alert Service
  - [x] 7.1 Write `backend/services/alert_service.py` — `check_and_alert(prediction_result, username, recipient_email)`: trigger if `hgb < 7.0` or `severity_level == "Severe"`; compose HTML email with patient username, HGB value, severity, timestamp, recommendation to act immediately
  - [x] 7.2 Implement retry loop — 3 attempts at 30s intervals using `time.sleep` in a background thread; update `alert_log` row with `delivery_status` ("sent"/"failed") and `retry_count` after each attempt
  - [x] 7.3 Implement `GET /api/alerts` (Admin only) and `POST /api/alerts/test` (Admin only) in `alerts_bp.py`
  - [x] 7.4 Write `backend/tests/test_alerts_properties.py` — Property 7 (alert email body contains username, HGB, severity, timestamp for any critical input), Property 8 (retry_count in alert_log never exceeds 3)

---

## Phase 5: Supporting Services

- [x] 8. Implement OCR Service
  - [x] 8.1 Write `backend/services/ocr_service.py` — `extract_cbc_from_file(filepath, mime_type)`: for PDF use pdf2image to convert first page to image; run pytesseract OCR; use regex patterns to extract CBC field values (e.g. `r'HGB\s*[:\-]?\s*(\d+\.?\d*)'`); assign confidence (High if regex match clean, Medium if partial, Low if inferred); return `{"values": {...}, "confidence": {...}, "warnings": [...]}`
  - [x] 8.2 Implement `POST /api/ocr/upload` in `ocr_bp.py` — validate MIME type (image/jpeg, image/png, application/pdf) and size ≤ 10MB before calling OCR; save to `tempfile`, delete within 60s after extraction; return partial results with per-field warnings
  - [x] 8.3 Write `backend/tests/test_ocr_properties.py` — Property 21 (oversized file or wrong MIME → 400 before ocr_service called, verified with mock)

- [x] 9. Implement Chatbot
  - [x] 9.1 Write `backend/services/chatbot_service.py` — intent classifier using keyword matching + response templates covering: anemia_definition, symptoms, types (iron/b12/folate/other), dietary_advice, when_to_see_doctor, cbc_interpretation, out_of_scope; no diagnosis/prescription responses — redirect to doctor for those intents; return `{"response": str, "intent": str}`
  - [x] 9.2 Implement session context — `ChatSession` class with `deque(maxlen=5)` storing last 5 (user, bot) pairs; sessions stored in module-level dict keyed by `session_id`; context injected into intent matching for follow-up questions
  - [x] 9.3 Implement `POST /api/chat/message` in `chat_bp.py` — accept `{"message": str, "session_id": str}`; create session if new; return response within 3s; require_auth

- [x] 10. Implement Model Retraining Pipeline
  - [x] 10.1 Implement `POST /api/retrain/upload` in `retrain_bp.py` — validate CSV has columns: rbc, mcv, mch, mchc, rdw, tlc, plt, hgb, label (case-insensitive); check all feature columns are numeric; reject with per-column error list if invalid; store valid CSV to `backend/retrain_uploads/`
  - [x] 10.2 Implement `POST /api/retrain/start` (Admin only) — load uploaded CSV + existing training data, auto-label using HGB thresholds if label column is missing severity, retrain RF + GB models on combined data with 80/20 split, compute accuracy/precision/recall/F1, store in `retrain_log`; run in background thread
  - [x] 10.3 Implement `GET /api/retrain/status` — return latest `retrain_log` row with status and metrics
  - [x] 10.4 Implement `POST /api/retrain/approve` (Admin only) — compare new vs current accuracy; if drop > 5pp return warning requiring `{"confirm": true}`; on approval backup current `.pkl` files to `backend/models/backup/`, copy new models to `backend/models/`, reload `PredictionService` singleton
  - [x] 10.5 Implement `POST /api/retrain/rollback` (Admin only) — restore `.pkl` files from `backend/models/backup/`, reload `PredictionService`
  - [x] 10.6 Write `backend/tests/test_retrain_properties.py` — Property 22 (any CSV missing required columns → 400 listing each missing column, no retrain_log row created)

---

## Phase 6: Admin Module

- [x] 11. Implement Admin Module
  - [x] 11.1 Implement `GET /api/stats` (Admin only) in `admin_bp.py` — query DB for: users by role count, total predictions, predictions by severity_level, predictions by anemia_type, total critical alerts sent, predictions per day last 30 days (for time-series chart)
  - [x] 11.2 Implement `GET /api/users` (Admin only) — support query params: `search` (username/email), `role` filter, `status` filter; return paginated list
  - [x] 11.3 Implement `POST /api/users` (Admin only) — create user with any role (patient/doctor/admin), bcrypt hash password, no OTP, return 201; log to `access_violation_log` with action="admin_create_user"
  - [x] 11.4 Implement `PATCH /api/users/<id>/deactivate` (Admin only) — set `status="inactive"`; if target is admin role require `{"confirm_admin_id": <id>}` of a second admin in request body; log action
  - [x] 11.5 Add audit logging middleware — wrap all admin Blueprint routes to log (admin_username, endpoint, method, timestamp) to `access_violation_log` with action prefix "admin_"

---

## Phase 7: PDF Report Generation

- [x] 12. Implement PDF Report Generation
  - [x] 12.1 Write `frontend/src/services/pdfService.js` — use `jsPDF` + `html2canvas`; capture the `#report-printable` DOM element; build PDF with: header (logo + "Anemia Detection Report"), patient name + date, CBC values table (8 rows), prediction result box (anemia detected, severity badge, type + confidence), SHAP explanation table (top-3 features with direction + value), diet recommendations list, health tips list, disclaimer footer; apply dark-to-light colour conversion for print
  - [x] 12.2 Enforce filename `anemia_report_{username}_{YYYYMMDD}.pdf` — derive date from prediction timestamp
  - [x] 12.3 Write `frontend/src/tests/pdf_properties.test.js` — Property 19 (filename regex match for any username/date combo), Property 20 (jsPDF output text contains all required field labels)

---

## Phase 8: Frontend — New Desktop-Application UI

> **UI Design System**: Dark sidebar (#0f1117) + light content panels (#f8f9fa). Typography: Inter font. Accent: #6366f1 (indigo). Density: compact (py-1.5 px-3 for table rows). No page scrolling — fixed viewport layout. Panels use internal scroll. Transitions: 150ms ease. Think Linear / VS Code / Notion.

- [x] 13. Set up frontend infrastructure
  - [x] 13.1 Install dependencies: `axios`, `react-router-dom`, `i18next`, `react-i18next`, `jspdf`, `html2canvas`, `lucide-react`; create `frontend/src/i18n/en.json`, `hi.json`, `ta.json` with all UI string keys
  - [x] 13.2 Create `frontend/src/api/client.js` — axios instance with baseURL from `VITE_API_URL` env var; request interceptor adds `Authorization: Bearer <token>` from localStorage; response interceptor redirects to `/login` on 401
  - [x] 13.3 Create `frontend/src/hooks/useAuth.js` — `login(token, user)` stores JWT + user object in localStorage; `logout()` clears storage + calls `/auth/logout`; `getRole()` decodes JWT payload; `isAuthenticated()` checks token expiry
  - [x] 13.4 Rewrite `frontend/src/App.jsx` — use `react-router-dom` v6 with `<Routes>`; protected `<PrivateRoute role="patient|doctor|admin">` component; routes: `/login`, `/register`, `/forgot-password`, `/patient/*`, `/doctor/*`, `/admin/*`; redirect based on role after login

- [x] 14. Implement authentication pages — desktop app style
  - [x] 14.1 Create `frontend/src/pages/LoginPage.jsx` — split layout: left panel (dark #0f1117) with app branding, animated CBC waveform SVG, tagline; right panel (white) with compact login form; no card shadow — full-height panels; keyboard shortcut Enter to submit
  - [x] 14.2 Create `frontend/src/pages/RegisterPage.jsx` — same split layout; step indicator (Step 1: Details → Step 2: Verify OTP); inline field validation with green checkmarks; OTP input as 6 separate single-digit boxes
  - [x] 14.3 Create `frontend/src/pages/ForgotPasswordPage.jsx` — 3-step flow (Email → OTP → New Password) with animated step progress bar; same split layout

- [x] 15. Implement shared components — desktop density
  - [x] 15.1 Create `frontend/src/components/CBCForm.jsx` — 2-column grid of compact numeric inputs; each field shows unit and reference range as hint text; real-time validation with red/green border; OCR upload button (paperclip icon) opens file picker; confidence badges (High/Med/Low) shown next to OCR-populated fields; keyboard Tab navigation optimised
  - [x] 15.2 Create `frontend/src/components/PredictionResult.jsx` — result panel with: top status bar (anemia detected/not with coloured left border), severity badge (pill: green/yellow/orange/red with icon), anemia type chip + confidence bar, SHAP explanation table (3 rows: feature | direction | impact bar)
  - [x] 15.3 Create `frontend/src/components/DietRecommendations.jsx` — collapsible section; food items as compact list rows with food name (bold) + rationale (muted); vegan items tagged with 🌱 badge; non-vegan items hidden when vegan filter active
  - [x] 15.4 Create `frontend/src/components/HealthTips.jsx` — numbered tip list with severity-coloured left accent bar; compact line height
  - [x] 15.5 Create `frontend/src/components/ReportHistory.jsx` — dense data table (20/page); columns: Date, HGB, Severity (badge), Type, Prediction, Actions; row hover highlight; click row → slide-in detail drawer from right; pagination controls at bottom
  - [x] 15.6 Create `frontend/src/components/HbTrendChart.jsx` — Recharts `<ComposedChart>`: LineChart of HGB vs date; 3 `<ReferenceLine>` at 11.9 (yellow), 9.9 (orange), 8.0 (red) with labels; custom dot coloured by severity; custom tooltip showing HGB, date, severity; empty state with dashed border and "Submit 2+ tests to see trend" message
  - [x] 15.7 Create `frontend/src/components/PDFDownloadButton.jsx` — icon button (download icon from lucide-react); loading spinner during generation; error toast (bottom-right) with retry on failure; success toast with filename
  - [x] 15.8 Create `frontend/src/components/LanguageSelector.jsx` — compact dropdown in sidebar footer; flag emoji + language name; on change: update i18next locale + PATCH `/api/users/me/language`; applies within 500ms

- [x] 16. Implement Patient Dashboard — desktop layout
  - [x] 16.1 Create `frontend/src/pages/PatientDashboard.jsx` — fixed layout: narrow dark sidebar (220px) + main content area; sidebar nav items: New Test (flask icon), History (table icon), Progress (chart icon), Chat (message icon); active item has indigo left border + light background; user avatar + name at sidebar bottom
  - [x] 16.2 New Test view: CBCForm on left (400px fixed) + PredictionResult panel on right (fills remaining width); result panel shows skeleton loader while predicting; after result: DietRecommendations + HealthTips in collapsible sections below result; PDFDownloadButton in result panel header

- [x] 17. Implement Doctor Dashboard — desktop layout
  - [x] 17.1 Create `frontend/src/pages/DoctorDashboard.jsx` — same sidebar layout as patient; nav items: New Assessment, Patient Records, Hb Trends, Alerts; critical alert count badge on Alerts nav item
  - [x] 17.2 New Assessment view: CBCForm with additional "Patient Username" field at top (required for doctor role); result displayed same as patient view
  - [x] 17.3 Alerts panel: list of critical alert notifications with patient name, HGB, severity, timestamp; unread alerts highlighted with red left border; mark-as-read on click

- [x] 18. Implement Admin Dashboard — desktop layout
  - [x] 18.1 Create `frontend/src/pages/AdminDashboard.jsx` — sidebar nav: Overview, Users, Alert Log, Retraining; top header bar shows system status indicators (DB: ✓, RF Model: ✓, GB Model: ✓)
  - [x] 18.2 Overview tab: 6 stat cards (total users, total predictions, by severity counts, critical alerts) + Recharts AreaChart (predictions/day last 30 days) + two small PieCharts (by severity, by anemia type)
  - [x] 18.3 Users tab: searchable/filterable table with inline "Deactivate" action; Create User form in a right-side panel (slides in); role badge colour-coded (patient=blue, doctor=green, admin=purple)
  - [x] 18.4 Create `frontend/src/components/AlertLog.jsx` — dense table: recipient, patient, HGB, severity, timestamp, status badge (sent=green, failed=red, pending=yellow); auto-refresh every 30s
  - [x] 18.5 Create `frontend/src/components/RetrainingPanel.jsx` — CSV upload dropzone; column validation feedback list; metrics display (accuracy/precision/recall/F1 as progress bars); Approve button (disabled if accuracy drop > 5pp without confirmation); Rollback button; status timeline

- [x] 19. Implement Chatbot widget
  - [x] 19.1 Create `frontend/src/components/Chatbot.jsx` — fixed bottom-right floating button (message icon, indigo); click opens chat panel (320px wide, 480px tall) sliding up from bottom-right; message bubbles (user=indigo right, bot=grey left); typing indicator (3 animated dots); session_id generated on mount with `crypto.randomUUID()`; input field with send button + Enter key support

---

## Phase 9: Multi-Language Support

- [x] 20. Complete multi-language support
  - [x] 20.1 Populate `en.json`, `hi.json`, `ta.json` — all UI labels, error messages, severity labels, anemia type names, diet item names, health tip strings, chatbot responses
  - [x] 20.2 Update `POST /api/predict` and `POST /api/chat/message` to read `Accept-Language` header; return diet recommendations, health tips, chatbot responses in requested language using per-language lookup dicts in recommendation_service and chatbot_service
  - [x] 20.3 Update `pdfService.js` to use current i18next locale for all PDF text labels
  - [x] 20.4 Add i18next `missingKeyHandler` that logs missing key to console and falls back to English value

---

## Phase 10: Testing and Verification

- [x] 21. Write remaining property-based tests
  - [x] 21.1 `backend/tests/test_reports_properties.py` — Property 12 (GET /api/reports never returns records from other users for patient/doctor role), Property 18 (pagination union = total N, no duplicates)
  - [x] 21.2 `backend/tests/test_pdf_properties.py` — Property 19 (filename pattern regex), Property 20 (PDF text contains all required field labels)

- [x] 22. Write frontend component tests
  - [x] 22.1 `frontend/src/tests/CBCForm.test.jsx` — empty submit shows validation errors, non-numeric input rejected, all-valid input enables submit button
  - [x] 22.2 `frontend/src/tests/PredictionResult.test.jsx` — snapshot for each severity level (None/Mild/Moderate/Severe) verifying correct badge colour class
  - [x] 22.3 `frontend/src/tests/HbTrendChart.test.jsx` — verify ReferenceLine props have y values 11.9, 9.9, 8.0

- [x] 23. Run smoke tests and fix issues
  - [x] 23.1 Verify `GET /health` returns 200 with both ML models loaded
  - [x] 23.2 Verify DB schema initialises on first run with all 6 tables present
  - [x] 23.3 Verify bcrypt cost factor = 12 by timing hash and checking rounds
  - [x] 23.4 Verify prediction latency < 2s: time 10 consecutive POST /api/predict calls
  - [x] 23.5 Run `pytest --cov=backend --cov-report=term-missing` — confirm ≥ 80% line coverage
  - [x] 23.6 Confirm all 22 correctness properties have at least one passing property test