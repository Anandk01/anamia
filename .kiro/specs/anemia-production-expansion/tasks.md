 #Implementation Tasks: AnemiaCare Production Expansion

## Task Overview

Expand the existing AnemiaCare system with 12 new modules. The base system (auth, prediction, reports, alerts, admin, OCR, chatbot, retraining, frontend dashboards) is already implemented. Tasks are ordered by dependency: database schema first, then backend services/blueprints, then frontend components.

---

## Phase 1: Database Schema Extension

- [x] 1. Extend database schema with all new tables
  - [x] 1.1 Add `doctor_patient` table to `backend/db.py` — columns: id (PK), doctor_id (FK user), patient_id (FK user), assigned_at; UNIQUE(doctor_id, patient_id)
  - [x] 1.2 Add `appointment` table — columns: appointment_id (PK), doctor_id (FK), patient_id (FK), requested_at, confirmed_at, slot_date (TEXT YYYY-MM-DD), slot_time (TEXT HH:MM), duration_min (DEFAULT 30), status (CHECK pending/confirmed/cancelled/completed), notes, cancellation_reason
  - [x] 1.3 Add `medication` table — columns: med_id (PK), username (FK), name, dose_mg (REAL), frequency (CHECK daily/twice/thrice/weekly), start_date, end_date, prescribed_by (FK), active (DEFAULT 1), created_at
  - [x] 1.4 Add `medication_log` table — columns: log_id (PK), med_id (FK), taken_at, skipped (DEFAULT 0), notes
  - [x] 1.5 Add `chat_room` table — columns: room_id (PK), doctor_id (FK), patient_id (FK), created_at, last_message_at; UNIQUE(doctor_id, patient_id)
  - [x] 1.6 Add `chat_message` table — columns: message_id (PK), room_id (FK), sender_username, content, message_type (CHECK text/file/image), file_url, read_at, created_at
  - [x] 1.7 Add `post` table — columns: post_id (PK), username (FK), title, body, tags (JSON), upvotes (DEFAULT 0), created_at, anonymous (DEFAULT 0), pinned (DEFAULT 0)
  - [x] 1.8 Add `reply` table — columns: reply_id (PK), post_id (FK), username (FK), body, is_doctor_verified (DEFAULT 0), upvotes (DEFAULT 0), created_at
  - [x] 1.9 Add `post_upvote` and `reply_upvote` tables — columns: id (PK), post_id/reply_id (FK), username; UNIQUE constraints
  - [x] 1.10 Add `article` table — columns: article_id (PK), title, content_md, summary, tags (JSON), author_id (FK), published_at, read_time_min, status (CHECK draft/published)
  - [x] 1.11 Add `bookmark` table — columns: bookmark_id (PK), username (FK), article_id (FK), created_at; UNIQUE(username, article_id)
  - [x] 1.12 Add `model_metrics` table — columns: metric_id (PK), model_name, accuracy (REAL), precision_score (REAL), recall (REAL), f1_score (REAL), auc_roc (REAL), confusion_matrix (JSON), dataset_name, dataset_size, trained_at
  - [x] 1.13 Add `notification` table — columns: notification_id (PK), username (FK), type (CHECK medication/appointment/checkup/alert/forum/system), title, message, read (DEFAULT 0), scheduled_at, sent_at, delivery_method (CHECK push/email/both), created_at
  - [x] 1.14 Add `prescription` table — columns: prescription_id (PK), doctor_id (FK username), patient_id (FK username), prediction_id (FK nullable), medications (JSON), dosage_instructions, duration_days, follow_up_date, notes, created_at
  - [x] 1.15 Add `audit_log` table — columns: audit_id (PK), actor, action, target, details (JSON), ip_address, timestamp
  - [x] 1.16 Extend `user` table with ALTER TABLE statements — add columns: blood_type, known_conditions (JSON), dietary_preferences (JSON), emergency_contact (JSON), specialization, license_number, available_hours (JSON), notification_prefs (JSON), theme_pref (DEFAULT 'light'), font_size (DEFAULT 'medium'), high_contrast (DEFAULT 0), onboarding_complete (DEFAULT 0)

---

## Phase 2: Backend Architecture Improvements

- [x] 2. Implement audit logging
  - [x] 2.1 Write `backend/services/audit_service.py` — function `log_action(actor, action, target, details, ip)` inserts into audit_log table; add audit logging calls to all admin actions, prescription creation, login attempts, and model retraining
  - [x] 2.2 Register audit logging in key blueprints — add audit_service.log_action calls to admin_bp (user create/deactivate), retrain_bp (retrain start/approve/rollback), auth_bp (login success/failure), prescriptions_bp (create)

---

## Phase 3: Appointment Booking Module

- [x] 3. Implement appointment booking backend
  - [x] 3.1 Write `backend/services/appointment_service.py` — functions: `request_appointment(patient_id, doctor_id, slot_date, slot_time, notes)` with conflict detection; `confirm_appointment(appointment_id, doctor_username)`; `cancel_appointment(appointment_id, username, reason)`; `get_calendar_view(user_id, role, week_start)`; `get_available_slots(doctor_id, date)` returns 30-min slots within doctor's available_hours; `has_conflict(doctor_id, slot_date, slot_time)` checks overlapping confirmed appointments
  - [x] 3.2 Write `backend/blueprints/appointments_bp.py` — Blueprint with prefix `/api/appointments`; endpoints: POST /request (patient), GET /calendar (patient+doctor, query: week_start), GET /:id, PUT /:id/confirm (doctor), PUT /:id/cancel (patient+doctor), PUT /:id/complete (doctor), GET /available-slots (patient, query: doctor_id, date); all require_auth + require_role
  - [x] 3.3 Register `appointments_bp` in `backend/app.py` — import and register blueprint with url_prefix

---

## Phase 4: Medication Tracker Module

- [x] 4. Implement medication tracker backend
  - [x] 4.1 Write `backend/services/medication_service.py` — functions: `prescribe_medication(doctor_username, patient_username, name, dose_mg, frequency, start_date, end_date)` creates medication entry; `get_todays_schedule(username)` returns meds due today with taken status; `log_medication(med_id, username, skipped, notes)` with duplicate prevention; `calculate_adherence(username, days=7)` returns {adherence_percent, total_doses, taken_doses, streak}; `deactivate_medication(med_id, doctor_username)`
  - [x] 4.2 Write `backend/blueprints/medication_bp.py` — Blueprint with prefix `/api/medications`; endpoints: POST / (doctor prescribes), GET / (patient+doctor, query: active), GET /schedule (patient, query: date), POST /:id/log (patient), GET /adherence (patient+doctor, query: days), PUT /:id/deactivate (doctor), GET /history (patient, query: med_id, page); all require_auth + require_role
  - [x] 4.3 Register `medication_bp` in `backend/app.py`

---

## Phase 5: Real-Time Messaging Module

- [x] 5. Implement WebSocket-based messaging
  - [x] 5.1 Add `flask-socketio`, `python-socketio`, `eventlet` to `backend/requirements.txt`
  - [x] 5.2 Write `backend/services/websocket_service.py` — SocketIO event handlers: `handle_connect(auth)` validates JWT and stores session; `handle_disconnect()` cleans up; `handle_join_room(data)` verifies membership and emits last 50 messages; `handle_send_message(data)` persists to chat_message, updates chat_room.last_message_at, emits to room; `handle_message_read(data)` updates read_at and emits ack; `handle_typing_start/stop(data)` emits typing indicators
  - [x] 5.3 Initialize Flask-SocketIO in `backend/app.py` — create SocketIO instance with cors_allowed_origins, register event handlers from websocket_service, configure eventlet async_mode
  - [x] 5.4 Add REST endpoints for chat room management — in existing `backend/blueprints/chat_bp.py` or new file: GET /api/chat/rooms (list user's rooms with last message), POST /api/chat/rooms (create room between doctor+patient), GET /api/chat/rooms/:id/messages (paginated history)

---

## Phase 6: Community Forum Module

- [x] 6. Implement community forum backend
  - [x] 6.1 Write `backend/services/forum_service.py` — functions: `create_post(username, title, body, tags, anonymous)` with validation; `get_posts(sort, page, tag)` with hot/top/new ranking; `upvote_post(post_id, username)` toggle; `create_reply(post_id, username, body)`; `upvote_reply(reply_id, username)` toggle; `verify_reply(reply_id, doctor_username)` sets is_doctor_verified=1; `delete_post(post_id, username, is_admin)` with permission check; `pin_post(post_id)` admin only; `rank_posts(posts, sort_by)` implements time-decay scoring for hot sort
  - [x] 6.2 Write `backend/blueprints/forum_bp.py` — Blueprint with prefix `/api/forum`; endpoints: GET /posts (query: sort, page, tag), POST /posts, GET /posts/:id (with replies), POST /posts/:id/replies, POST /posts/:id/upvote, POST /replies/:id/upvote, PUT /replies/:id/verify (doctor), DELETE /posts/:id (author+admin), GET /tags; all require_auth
  - [x] 6.3 Register `forum_bp` in `backend/app.py`

---

## Phase 7: Education Center Module

- [x] 7. Implement education center backend
  - [x] 7.1 Write `backend/services/education_service.py` — functions: `create_article(author_id, title, content_md, tags)` calculates read_time_min (word_count/200 rounded up); `generate_summary(content_md)` calls Gemini API with fallback to first 200 chars; `publish_article(article_id, author_id)` sets status=published and published_at; `search_articles(query, tag, page)` with text search on title+content; `toggle_bookmark(username, article_id)` adds/removes bookmark
  - [x] 7.2 Write `backend/blueprints/education_bp.py` — Blueprint with prefix `/api/articles`; endpoints: GET / (query: status, page, tag, search), POST / (doctor+admin), GET /:id, PUT /:id (author), POST /:id/publish (author), POST /:id/bookmark (all), GET /bookmarks (all); require_auth + require_role
  - [x] 7.3 Register `education_bp` in `backend/app.py`

---

## Phase 8: ML Model Upgrades

- [x] 8. Implement ML model evaluation and comparison
  - [x] 8.1 Write `backend/services/model_evaluation_service.py` — functions: `evaluate_model(model, X_test, y_test, model_name)` computes accuracy, precision, recall, F1, AUC-ROC, confusion matrix and stores in model_metrics table; `detect_drift(model_name, new_metrics)` compares against baseline with 5% threshold; `train_all_models(dataset_path)` trains RF, GB, XGBoost, LightGBM on given dataset with 80/20 split, returns metrics dict for each
  - [x] 8.2 Add `xgboost` and `lightgbm` to `backend/requirements.txt`
  - [x] 8.3 Extend `backend/blueprints/retrain_bp.py` — update POST /api/retrain/start to train all 4 models; add GET /api/retrain/metrics endpoint returning model_metrics for all models; add GET /api/retrain/comparison returning side-by-side metrics table
  - [x] 8.4 Write training script update in `backend/train_supervised.py` — add XGBoost and LightGBM training alongside existing RF and GB; save all 4 models to backend/models/; print comparative metrics table

---

## Phase 9: Smart Reminders & Notifications

- [x] 9. Implement notification system
  - [x] 9.1 Write `backend/services/notification_service.py` — functions: `create_notification(username, type, title, message, delivery_method, scheduled_at)` inserts into notification table; `schedule_medication_reminders(username)` creates notifications based on active medications; `schedule_appointment_reminder(appointment_id)` creates 24h and 1h reminders; `send_notification(notification_id)` delivers via push (WebSocket emit) and/or email; `get_unread_count(username)` returns count
  - [x] 9.2 Write `backend/blueprints/notifications_bp.py` — Blueprint with prefix `/api/notifications`; endpoints: GET / (query: read, page, type), GET /unread-count, PUT /:id/read, PUT /read-all, DELETE /:id; all require_auth
  - [x] 9.3 Register `notifications_bp` in `backend/app.py`
  - [x] 9.4 Integrate notification triggers — call schedule_appointment_reminder when appointment confirmed; call schedule_medication_reminders when medication prescribed; emit real-time notifications via WebSocket

---

## Phase 10: Prescription Module

- [x] 10. Implement prescription system
  - [x] 10.1 Write `backend/blueprints/prescriptions_bp.py` — Blueprint with prefix `/api/prescriptions`; endpoints: POST / (doctor: create prescription with medications JSON, optional prediction_id link), GET / (doctor: list prescriptions, query: patient_username, page), GET /mine (patient: own prescriptions), GET /:id (doctor+patient), GET /:id/pdf (generate PDF); require_auth + require_role
  - [x] 10.2 Implement prescription PDF generation — use reportlab or similar to generate prescription PDF with doctor name, patient name, date, medications table (name, dose, frequency, duration), dosage instructions, follow-up date, and disclaimer
  - [x] 10.3 Integrate with medication tracker — when prescription created with auto_create_meds=true, call medication_service.prescribe_medication for each medication in the list
  - [x] 10.4 Register `prescriptions_bp` in `backend/app.py`

---

## Phase 11: Advanced Analytics

- [x] 11. Implement analytics endpoints
  - [x] 11.1 Write `backend/services/analytics_service.py` — functions: `get_overview_metrics(doctor_username, date_range)` aggregates predictions, appointments, adherence; `get_trend_data(metric, period_days)` returns time-series for predictions/appointments/users/adherence; `get_adherence_summary(doctor_username)` returns avg adherence across patients; `get_appointments_summary(period_days)` returns total/completed/cancelled/no-show; `get_system_health()` returns db_size, active_users, queue_depth
  - [x] 11.2 Write `backend/blueprints/analytics_bp.py` — Blueprint with prefix `/api/analytics`; endpoints: GET /overview (doctor+admin), GET /trends (query: metric, period), GET /adherence-summary (doctor), GET /appointments-summary (doctor+admin), GET /model-performance (admin), GET /system-health (admin); require_auth + require_role
  - [x] 11.3 Register `analytics_bp` in `backend/app.py`

---

## Phase 12: Profile & Settings

- [x] 12. Implement profile and settings backend
  - [x] 12.1 Write `backend/services/profile_service.py` — functions: `get_profile(username)` returns full profile with health data; `update_health_profile(username, data)` updates blood_type, conditions, dietary_prefs, emergency_contact with validation; `update_preferences(username, prefs)` updates theme, font_size, high_contrast, language, notification_prefs; `update_available_hours(username, hours)` for doctors; `change_password(username, current, new)` with bcrypt verification
  - [x] 12.2 Write `backend/blueprints/profile_bp.py` — Blueprint with prefix `/api/profile`; endpoints: GET / (all), PUT / (all: health profile), PUT /preferences (all), PUT /password (all), PUT /available-hours (doctor); require_auth + require_role
  - [x] 12.3 Register `profile_bp` in `backend/app.py`

---

## Phase 13: Frontend — Appointment Components

- [x] 13. Implement appointment frontend components
  - [x] 13.1 Create `frontend/src/components/AppointmentCalendar.jsx` — weekly calendar view using CSS grid; columns for each day (Mon-Sun); rows for 30-min time slots; appointments shown as colored blocks (pending=yellow, confirmed=green, cancelled=grey); click slot to open BookingModal (patient) or view details (doctor); navigation arrows for week switching
  - [x] 13.2 Create `frontend/src/components/BookingModal.jsx` — modal for patients: select doctor (from assigned doctors), pick date (date picker), see available slots (fetched from /available-slots), add notes; submit calls POST /appointments/request; loading state and success/error feedback
  - [x] 13.3 Create `frontend/src/components/DoctorSchedule.jsx` — doctor view: list of pending appointment requests with patient name, date, time, notes; Accept/Decline buttons; confirmed appointments list; today's schedule highlighted

---

## Phase 14: Frontend — Medication Tracker Components

- [x] 14. Implement medication tracker frontend
  - [x] 14.1 Create `frontend/src/components/MedicationTracker.jsx` — today's schedule view: list of medications due with check-off buttons; each item shows name, dose, frequency, time; checked items show green checkmark with timestamp; skip button with optional notes; adherence streak counter at top; "Add Medication" button for self-added meds
  - [x] 14.2 Create `frontend/src/components/AdherenceChart.jsx` — Recharts BarChart showing daily adherence % over last 7/30 days; color-coded bars (green >80%, yellow 50-80%, red <50%); horizontal reference line at 80% target; tooltip with exact percentage and doses taken/expected
  - [x] 14.3 Create `frontend/src/components/PrescribeMedication.jsx` — doctor form: patient username, medication name, dose_mg, frequency dropdown, start_date, end_date (optional); submit calls POST /medications; success shows confirmation

---

## Phase 15: Frontend — Real-Time Chat Components

- [x] 15. Implement real-time messaging frontend
  - [x] 15.1 Install `socket.io-client` in frontend; create `frontend/src/contexts/SocketContext.jsx` — React context providing socket instance; connects on auth with JWT; handles reconnection; provides emit/on helpers
  - [x] 15.2 Create `frontend/src/components/ChatRoomList.jsx` — list of chat rooms with last message preview, other user's name, unread count badge, timestamp; click opens DoctorChat; sorted by last_message_at descending
  - [x] 15.3 Create `frontend/src/components/DoctorChat.jsx` — full chat interface: message bubbles (sent=right indigo, received=left grey); file/image attachment button; typing indicator (3 dots animation); read receipts (double checkmark); auto-scroll to bottom on new message; input field with send button + Enter key; loads last 50 messages on room join via WebSocket

---

## Phase 16: Frontend — Forum Components

- [x] 16. Implement community forum frontend
  - [x] 16.1 Create `frontend/src/components/Forum.jsx` — post list with sort tabs (Hot/Top/New); tag filter pills; each post card shows: title, body preview (100 chars), author (or "Anonymous"), upvote count + button, reply count, tags, timestamp; pagination; "New Post" button
  - [x] 16.2 Create `frontend/src/components/PostDetail.jsx` — full post view with title, body, author, tags, upvotes; replies list below with upvote buttons; doctor replies show green "Verified Doctor" badge; reply input form at bottom; doctor "Verify" button on replies
  - [x] 16.3 Create `frontend/src/components/CreatePost.jsx` — form: title input, body textarea (Markdown supported), tag input (comma-separated, max 5), anonymous toggle checkbox; submit calls POST /api/forum/posts

---

## Phase 17: Frontend — Education Center Components

- [x] 17. Implement education center frontend
  - [x] 17.1 Create `frontend/src/components/EducationCenter.jsx` — card grid layout; each card: title, summary (2 lines), tags as pills, read time, author; search bar at top; tag filter buttons; bookmark icon on each card; pagination
  - [x] 17.2 Create `frontend/src/components/ArticleReader.jsx` — full article view: title, author, published date, read time, tags; Markdown content rendered with react-markdown; bookmark button in header; back button to list
  - [x] 17.3 Create `frontend/src/components/ArticleEditor.jsx` — doctor/admin form: title input, Markdown editor (textarea with preview toggle), tags input; save as draft or publish; shows generated summary after publish

---

## Phase 18: Frontend — Analytics & ML Components

- [ ] 18. Implement analytics and model comparison frontend
  - [-] 18.1 Create `frontend/src/components/AnalyticsDashboard.jsx` — stat cards row (total patients, predictions, avg adherence, appointments); Recharts AreaChart for trends (predictions/day); PieCharts for severity and type distribution; date range selector
  - [ ] 18.2 Create `frontend/src/components/ModelComparison.jsx` — table with columns: Model Name, Accuracy, Precision, Recall, F1, AUC-ROC, Trained At; rows for RF, GB, XGBoost, LightGBM; best value in each column highlighted green; confusion matrix heatmap below (selectable per model) using Recharts or custom grid with color intensity

---

## Phase 19: Frontend — Notifications & Prescriptions

- [ ] 19. Implement notification and prescription frontend
  - [ ] 19.1 Create `frontend/src/components/NotificationBell.jsx` — bell icon in header with red badge showing unread count; click opens dropdown with last 5 notifications; "View All" link to NotificationCenter; real-time updates via WebSocket
  - [ ] 19.2 Create `frontend/src/components/NotificationCenter.jsx` — full page list of all notifications; filter by type tabs; mark as read on click; "Mark All Read" button; each item shows: icon by type, title, message, timestamp, read/unread indicator
  - [ ] 19.3 Create `frontend/src/components/PrescriptionView.jsx` — patient view: list of prescriptions with doctor name, date, medication count; click expands to show full medication table (name, dose, frequency, duration); "Download PDF" button
  - [ ] 19.4 Create `frontend/src/components/PrescriptionForm.jsx` — doctor form: select patient, link to prediction (optional), dynamic medication list (add/remove rows: name, dose, frequency, duration), dosage instructions textarea, duration_days, follow_up_date picker, notes; submit creates prescription

---

## Phase 20: Frontend — UX Improvements

- [ ] 20. Implement PWA, dark mode, onboarding, and accessibility
  - [ ] 20.1 Create `frontend/public/manifest.json` — PWA manifest with app name "AnemiaCare", icons, theme_color, background_color, display: standalone; create `frontend/public/sw.js` service worker with cache-first strategy for static assets and network-first for API calls
  - [ ] 20.2 Create `frontend/src/contexts/ThemeContext.jsx` — React context for dark/light/system theme; reads system preference via matchMedia; stores preference in localStorage + syncs to server; applies Tailwind dark class to html element
  - [ ] 20.3 Create `frontend/src/components/DarkModeToggle.jsx` — three-state toggle (Light/Dark/System) in settings; icon changes based on current theme
  - [ ] 20.4 Create `frontend/src/components/OnboardingWizard.jsx` — multi-step wizard shown on first login for patients: Step 1 (health profile: blood type, conditions, dietary prefs), Step 2 (link to doctor: select from available doctors), Step 3 (first CBC guidance: explanation + link to New Test); marks onboarding_complete=1 on finish
  - [ ] 20.5 Create `frontend/src/components/LoadingSkeleton.jsx` — reusable skeleton component with variants: card, table-row, text-block, chart; uses Tailwind animate-pulse; replace all existing spinners with appropriate skeleton variants
  - [ ] 20.6 Add accessibility improvements — add aria-labels to all interactive elements; ensure keyboard navigation (Tab order, Enter/Space activation); add focus-visible styles; verify color contrast ratios meet WCAG AA (4.5:1 for text); add skip-to-content link

---

## Phase 21: Frontend — Profile & Settings

- [ ] 21. Implement profile and settings frontend
  - [ ] 21.1 Create `frontend/src/components/ProfileSettings.jsx` — tabbed interface: Personal Info (name, email read-only, blood type, conditions multi-select, dietary prefs checkboxes, emergency contact form), Notifications (toggle grid: email/push per type), Accessibility (font size S/M/L radio, high contrast toggle, reduced motion toggle), Security (change password form)
  - [ ] 21.2 Create `frontend/src/components/DoctorAvailability.jsx` — weekly schedule editor: for each day (Mon-Sun) toggle available + set start/end time; save calls PUT /api/profile/available-hours

---

## Phase 22: Dashboard Integration & Feature-Dense UI

- [ ] 22. Integrate new modules into existing dashboards with maximum visible features
  - [ ] 22.1 Update `frontend/src/pages/PatientDashboard.jsx` — expand sidebar to show ALL module nav items visible at once (no collapsing): Home (grid icon), New Test (flask icon), History (table icon), Progress (chart icon), Appointments (calendar icon), Medications (pill icon), Messages (chat icon), Forum (users icon), Education (book icon), Prescriptions (clipboard icon), Diet Plan (apple icon), Symptom Checker (stethoscope icon), Settings (gear icon); add NotificationBell + unread badge to header; add quick-stats bar below header showing: "Next Appointment: Tomorrow 10:00", "Medications Due: 2", "Adherence: 87%", "Unread Messages: 3"; show OnboardingWizard on first login
  - [ ] 22.2 Create Patient Home/Overview tab — visible by default on login; show 4 stat cards row (HGB Latest, Severity Status, Adherence %, Next Appointment); below: 2-column layout with HbTrendChart (left, 60% width) + Today's Medications checklist (right, 40%); below that: Recent Notifications list (last 5) + Quick Actions grid (Book Appointment, Start CBC Test, Open Chat, View Reports — 4 icon buttons in a row)
  - [ ] 22.3 Update `frontend/src/pages/DoctorDashboard.jsx` — expand sidebar: Home (grid icon), New Assessment (flask icon), Patient Records (table icon), Schedule (calendar icon), Prescribe (clipboard icon), Messages (chat icon), Forum (users icon), Articles (book icon), Analytics (chart icon), Alerts (bell icon), Hb Trends (chart icon), Settings (gear icon); add NotificationBell + pending appointment count badge to header; add quick-stats bar: "Patients: 12", "Pending Appointments: 4", "Critical Alerts: 2", "Avg Adherence: 78%"
  - [ ] 22.4 Create Doctor Home/Overview tab — 6 stat cards (Total Patients, Today's Appointments, Pending Requests, Critical Alerts, Avg Patient Adherence, Predictions This Week); below: 2-column with Today's Schedule timeline (left) + Recent Critical Alerts list (right); below: Patient Adherence Leaderboard (top 5 patients by adherence %) + Quick Actions (New Assessment, Write Prescription, View Schedule, Publish Article)
  - [ ] 22.5 Update `frontend/src/pages/AdminDashboard.jsx` — expand sidebar: Overview (grid icon), Users (users icon), Predictions (brain icon), Analytics (chart icon), Model Comparison (layers icon), Retraining (refresh icon), Alert Log (bell icon), Audit Log (shield icon), Forum Moderation (flag icon), Articles (book icon), System Health (server icon), Settings (gear icon); add system status indicators in header (DB: ✓, Models: ✓, WebSocket: ✓, Queue: ✓)
  - [ ] 22.6 Create Admin Home/Overview tab — 8 stat cards in 2 rows (Total Users, Patients, Doctors, Predictions Today, Critical Alerts, Model Accuracy, Forum Posts, Articles Published); below: Recharts AreaChart (predictions/day 30 days) spanning full width; below: 3-column layout with PieChart (severity distribution) + PieChart (anemia type distribution) + BarChart (users registered per week); below: Recent Audit Log (last 10 entries) + System Health metrics (API latency, DB size, active sessions)
  - [ ] 22.7 Add feature badges and counts throughout — every sidebar nav item shows a count badge where applicable (Messages: unread count, Appointments: pending count, Alerts: critical count, Forum: new posts today, Medications: due today); use red for urgent, blue for informational
  - [ ] 22.8 Add breadcrumb navigation to all pages — show current location path (e.g., "Dashboard > Appointments > Calendar View") below the header bar; adds visual depth and navigation context
  - [ ] 22.9 Add footer bar to all dashboards — fixed bottom bar (24px height) showing: connection status indicator (green dot + "Connected"), current language, last sync time, app version "v2.0.0"; subtle but adds production feel

---

## Phase 23: Testing

- [ ] 23. Write tests for new modules
  - [ ] 23.1 Write `backend/tests/test_appointments.py` — test appointment creation, conflict detection, confirm/cancel flows, available slots calculation, role-based access
  - [ ] 23.2 Write `backend/tests/test_medications.py` — test medication CRUD, adherence calculation, streak counting, duplicate log prevention, schedule generation
  - [ ] 23.3 Write `backend/tests/test_forum.py` — test post CRUD, upvote toggle, reply creation, doctor verification, anonymous posting, sorting algorithms
  - [ ] 23.4 Write `backend/tests/test_education.py` — test article CRUD, read time calculation, bookmark toggle, search functionality
  - [ ] 23.5 Write `backend/tests/test_notifications.py` — test notification creation, delivery, read marking, unread count
  - [ ] 23.6 Write `backend/tests/test_prescriptions.py` — test prescription creation, PDF generation, auto-medication creation, role access
  - [ ] 23.7 Write `backend/tests/test_model_evaluation.py` — test metrics computation, drift detection algorithm, model comparison
  - [ ] 23.8 Write `backend/tests/test_audit_log.py` — test audit log creation, querying, filtering by actor/action
  - [ ] 23.9 Run full test suite — `pytest backend/tests/ --cov=backend --cov-report=term-missing`; verify all new tests pass; confirm coverage remains ≥ 80%
