# Requirements Document: AnemiaCare Production Expansion

## Introduction

This document defines the requirements for expanding the existing AnemiaCare system from a college-project prototype into a production-grade clinical platform. The expansion adds 12 major modules on top of the already-implemented base system (auth, prediction, reports, alerts, admin, OCR, chatbot, retraining, frontend dashboards). New modules include: Appointment Booking, Medication Tracker, Real-Time Messaging, Community Forum, Education Center, ML Model Upgrades, Smart Reminders, Prescription Module, Advanced Analytics, Backend Architecture Improvements (2FA, refresh tokens, audit logging), Frontend UX Improvements (PWA, dark mode, accessibility, onboarding), and Profile/Settings Enhancement.

---

## Glossary

- **Appointment**: A scheduled consultation between a Doctor and Patient with date, time, and status.
- **Medication**: A prescribed or self-added drug entry with dosage, frequency, and active period.
- **Adherence**: The percentage of prescribed medication doses actually taken over a time period.
- **Chat Room**: A WebSocket-based messaging channel between one Doctor and one Patient.
- **Forum Post**: A user-created discussion thread in the community forum.
- **Article**: An educational content piece authored by Doctors or Admins, published in the Education Center.
- **Prescription**: A formal digital prescription issued by a Doctor post-diagnosis.
- **Notification**: A push/email alert for medication reminders, appointment updates, or system events.
- **Model Drift**: A degradation in ML model performance metrics compared to the baseline.
- **2FA/TOTP**: Two-Factor Authentication using Time-based One-Time Passwords.
- **Refresh Token**: A long-lived token used to obtain new access tokens without re-authentication.
- **PWA**: Progressive Web App — enables offline access and install-to-homescreen.

---

## Requirements

### Requirement 1: Appointment Booking System

**User Story:** As a Patient, I want to book appointments with my assigned Doctor, so that I can schedule consultations without phone calls or in-person visits.

#### Acceptance Criteria

1. WHEN a Patient submits an appointment request with a valid doctor_id, slot_date (future date), and slot_time (within doctor's available hours), THE System SHALL create an appointment with status "pending" and notify the Doctor.
2. WHEN a Doctor confirms a pending appointment, THE System SHALL update the status to "confirmed", set confirmed_at timestamp, and notify the Patient.
3. WHEN a Doctor or Patient cancels an appointment, THE System SHALL update the status to "cancelled" and notify the other party.
4. THE System SHALL prevent double-booking by rejecting appointment requests that conflict with existing confirmed appointments for the same Doctor within a 30-minute window.
5. WHEN a Patient requests available slots for a Doctor on a given date, THE System SHALL return all 30-minute slots within the Doctor's configured available hours, marking each as available or unavailable.
6. THE System SHALL display a weekly calendar view showing all appointments for the logged-in user (Patient sees their bookings, Doctor sees their schedule).
7. THE System SHALL support a doctor_patient assignment table so that Patients can only book with their assigned Doctor.

---

### Requirement 2: Medication Tracker

**User Story:** As a Patient, I want to track my prescribed medications and log when I take them, so that I can maintain adherence and share progress with my Doctor.

#### Acceptance Criteria

1. WHEN a Doctor prescribes a medication for a Patient, THE System SHALL create a medication entry with name, dose_mg, frequency (daily/twice/thrice/weekly), start_date, end_date, and prescribed_by fields.
2. WHEN a Patient views their medication schedule for today, THE System SHALL display all active medications due based on their frequency, with check-off buttons for each dose.
3. WHEN a Patient logs a medication dose (taken or skipped), THE System SHALL record the entry in medication_log with timestamp and skipped flag.
4. WHEN a Patient or Doctor requests adherence data, THE System SHALL calculate adherence_percent as (taken_doses / expected_doses) × 100 over the specified period (default 7 days).
5. THE System SHALL calculate and display a streak counter showing consecutive days with all doses taken.
6. THE System SHALL prevent duplicate logs for the same medication within the same dose window.
7. WHEN a Doctor deactivates a medication, THE System SHALL set active=0 and exclude it from future schedules.

---

### Requirement 3: Real-Time Messaging

**User Story:** As a Patient, I want to send messages to my Doctor in real-time, so that I can ask questions and share reports without waiting for appointments.

#### Acceptance Criteria

1. THE System SHALL establish WebSocket connections using Flask-SocketIO with JWT authentication on connect.
2. WHEN a user joins a chat room, THE System SHALL verify room membership (user is either the doctor_id or patient_id of the room) before allowing access.
3. WHEN a user sends a message, THE System SHALL persist it to the chat_message table and emit it to all room members in real-time.
4. THE System SHALL support message types: text, file, and image, with file_url for non-text messages.
5. WHEN a user marks a message as read, THE System SHALL update the read_at timestamp and emit a read receipt to the sender.
6. THE System SHALL display typing indicators when a user is composing a message.
7. THE System SHALL show unread message count badges on the dashboard for both Patient and Doctor roles.
8. THE System SHALL load the last 50 messages when a user joins a room.

---

### Requirement 4: Community Forum

**User Story:** As a Patient, I want to ask questions and share experiences in a community forum, so that I can learn from others managing anemia.

#### Acceptance Criteria

1. WHEN a user creates a forum post with title (5-200 chars), body (10-10000 chars), and optional tags (0-5), THE System SHALL persist it and make it visible to all authenticated users.
2. THE System SHALL support anonymous posting where the username is stored but not displayed in API responses.
3. WHEN a user upvotes a post or reply, THE System SHALL toggle the upvote (add if not exists, remove if exists) and update the total count.
4. WHEN a Doctor replies to a post, THE System SHALL display a green "Verified Doctor" badge on their reply.
5. WHEN a Doctor marks a reply as "doctor-verified", THE System SHALL set is_doctor_verified=1 and display a verification badge.
6. THE System SHALL support post sorting by: hot (time-decay algorithm), top (most upvotes), and new (most recent).
7. THE Admin SHALL be able to pin and delete any post.
8. THE System SHALL support tag-based filtering of posts.

---

### Requirement 5: Education Center

**User Story:** As a Patient, I want to read educational articles about anemia, so that I can better understand my condition and treatment options.

#### Acceptance Criteria

1. WHEN a Doctor or Admin creates an article with title, content_md (Markdown), and tags, THE System SHALL calculate read_time_min and generate a summary using Gemini API.
2. WHEN an article is published, THE System SHALL make it visible to all authenticated users with tag filtering and search capabilities.
3. WHEN a user bookmarks an article, THE System SHALL persist the bookmark and allow retrieval via a bookmarks endpoint.
4. THE System SHALL display articles in a card grid with title, summary, tags, read time, and author name.
5. THE System SHALL render article content as Markdown with proper formatting.
6. IF the Gemini API fails during summary generation, THE System SHALL use the first 200 characters of content as a fallback summary.

---

### Requirement 6: ML Model Upgrades

**User Story:** As an Admin, I want to train and compare multiple ML models (RF, GB, XGBoost, LightGBM) on real datasets with proper evaluation metrics, so that evaluators can see rigorous ML methodology.

#### Acceptance Criteria

1. THE System SHALL train XGBoost and LightGBM classifiers alongside existing Random Forest and Gradient Boosting models.
2. THE System SHALL evaluate all models using: accuracy, precision, recall, F1-score, AUC-ROC, and confusion matrix.
3. THE System SHALL store evaluation metrics in a model_metrics table with model_name, all metric values, dataset info, and training timestamp.
4. THE System SHALL display a model comparison table in the Admin Dashboard showing all models side-by-side.
5. THE System SHALL implement drift detection that compares new model metrics against the baseline and flags degradation > 5% relative.
6. THE System SHALL display confusion matrix heatmaps for each model in the Admin Dashboard.
7. WHEN retraining is triggered, THE System SHALL train all four models and present comparative results before approval.

---

### Requirement 7: Smart Reminders & Notifications

**User Story:** As a Patient, I want to receive reminders for medications and upcoming appointments, so that I don't miss doses or consultations.

#### Acceptance Criteria

1. THE System SHALL schedule medication reminders based on each medication's frequency and the patient's notification preferences.
2. THE System SHALL send appointment reminders 24 hours and 1 hour before confirmed appointments.
3. THE System SHALL support delivery methods: push (WebSocket), email, or both, configurable per user.
4. THE System SHALL display a notification bell icon with unread count in the dashboard header.
5. THE System SHALL provide a notification center page listing all notifications with read/unread status.
6. WHEN a user marks a notification as read, THE System SHALL update the read flag.
7. THE System SHALL support notification types: medication, appointment, checkup, alert, forum, system.

---

### Requirement 8: Prescription Module

**User Story:** As a Doctor, I want to issue digital prescriptions after diagnosis, so that Patients have a formal record of their treatment plan.

#### Acceptance Criteria

1. WHEN a Doctor creates a prescription with patient_username, medications list (name, dose, frequency, duration), and optional prediction_id link, THE System SHALL persist it and notify the Patient.
2. THE System SHALL allow Patients to view all their prescriptions with doctor name, date, and medication details.
3. THE System SHALL generate a downloadable PDF of any prescription.
4. WHEN a prescription is created, THE System SHALL optionally auto-create medication entries for the Patient's medication tracker.
5. THE System SHALL create an audit log entry for every prescription created.
6. THE System SHALL support follow_up_date and duration_days fields for treatment planning.

---

### Requirement 9: Advanced Analytics Dashboard

**User Story:** As a Doctor or Admin, I want to see aggregated analytics about patient outcomes, appointment utilization, and medication adherence, so that I can identify trends and improve care.

#### Acceptance Criteria

1. THE System SHALL provide an overview endpoint returning: total patients, total predictions, severity distribution, type distribution, and average adherence.
2. THE System SHALL provide time-series trend data for: predictions per day, appointments per day, new users per day, and adherence over time.
3. THE Doctor view SHALL be scoped to their assigned patients only.
4. THE Admin view SHALL show system-wide metrics.
5. THE System SHALL provide appointment summary metrics: total, completed, cancelled, and no-show rate.
6. THE System SHALL provide model performance metrics accessible to Admin.

---

### Requirement 10: Backend Architecture Improvements

**User Story:** As a system operator, I want comprehensive audit logging, so that the system meets production security standards and all significant actions are traceable.

#### Acceptance Criteria

1. THE System SHALL log all significant actions (user creation, deactivation, prescription creation, model retraining, login attempts) to an audit_log table with actor, action, target, details, ip_address, and timestamp.
2. THE System SHALL provide an audit log viewer for Admin users.
3. THE System SHALL record failed authentication attempts with username, IP address, and timestamp.

---

### Requirement 11: Frontend UX Improvements

**User Story:** As a Patient, I want the application to work offline, support dark mode, and guide me through onboarding, so that I have a polished, accessible experience.

#### Acceptance Criteria

1. THE System SHALL implement PWA support with a service worker for offline caching of patient history and static assets.
2. THE System SHALL support dark mode with system-preference detection and a manual toggle, persisted per user.
3. THE System SHALL provide a multi-step onboarding wizard for new patients: health profile setup, doctor linking, and first CBC entry guidance.
4. THE System SHALL use loading skeleton screens instead of spinners for all data-loading states.
5. THE System SHALL meet WCAG 2.1 AA accessibility standards: aria-labels, keyboard navigation, focus states, and sufficient color contrast.
6. THE System SHALL support configurable font size (S/M/L) and high-contrast mode.

---

### Requirement 12: Profile & Settings Enhancement

**User Story:** As a user, I want to manage my health profile, notification preferences, and accessibility settings, so that the system is personalized to my needs.

#### Acceptance Criteria

1. THE System SHALL allow Patients to set: blood_type, known_conditions (JSON array), dietary_preferences (JSON array), and emergency_contact (JSON object).
2. THE System SHALL allow Doctors to set: specialization, license_number, and available_hours (weekly schedule).
3. THE System SHALL allow all users to configure notification preferences (email/push per notification type).
4. THE System SHALL allow all users to change their password with current password verification.
5. THE System SHALL persist theme preference (light/dark/system), font size, and high contrast settings.
6. THE System SHALL mark onboarding as complete after the wizard is finished.
