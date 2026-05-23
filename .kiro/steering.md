# AnemiaCare — Kiro Project Steering

## How to use these specs

Read and implement specs in this exact order. Each spec depends on the previous one.
Do NOT implement a later spec before the earlier ones are complete and tested.

## Implementation order

| Order | File | What it builds | Depends on |
|-------|------|----------------|------------|
| 1 | 01-doctor-patient-assignment.md | doctor_patient table + assignment endpoints + admin UI | Nothing |
| 2 | 02-global-socket-context.md | Flask-SocketIO + React SocketContext | Nothing |
| 3 | 03-appointment-booking.md | Full booking pipeline (patient→doctor→patient) | 01, 02 |
| 4 | 04-prediction-alert-pipeline.md | CBC prediction→patient live update→auto alerts | 01, 02 |
| 5 | 05-realtime-messaging.md | Doctor–patient live chat | 01, 02 |
| 6 | 06-medication-tracker.md | Prescribe→track→remind pipeline | 01, 02, 04 |

## Critical rules — read before generating any code

### Rule 1: Never build isolated pages
Every feature connects at least two roles. The acceptance criteria in each spec
lists the cross-role interactions that MUST work. Do not mark a feature done
until ALL acceptance criteria pass.

### Rule 2: The notify_user pattern
Every cross-role action uses this pattern:
1. Save to database
2. Call notify_user(recipient, event_name, payload) from utils.py
3. Insert a notification row for the recipient
4. Return HTTP response to the caller

Never skip steps 2 or 3.

### Rule 3: Role filtering is mandatory
- Doctors ONLY see their assigned patients (use get_patients_for_doctor())
- Patients ONLY see their assigned doctor (use get_doctor_for_patient())
- Admins see everything
- Every GET endpoint that returns patient data MUST enforce this

### Rule 4: The global socket context is the single source of truth
- Badge counts (unread messages, pending appointments, active alerts) come ONLY from SocketContext
- Never fetch badge counts from API on every render — let socket events update them
- Page-level socket subscriptions use addListener/removeListener pattern

### Rule 5: Test the end-to-end flow, not just the page
After each spec, test by opening two browser tabs:
- Tab 1: logged in as patient
- Tab 2: logged in as doctor
Perform the action in Tab 1. Verify Tab 2 updates without refreshing.

## Tech stack reminder
- Backend: Flask + Flask-SocketIO + SQLite (or PostgreSQL)
- Auth: JWT (flask-jwt-extended)
- Email: Flask-Mail
- Background tasks: Celery + Redis
- Frontend: React 19 + Vite + Tailwind CSS v4
- Real-time: socket.io-client (frontend) + Flask-SocketIO (backend)

## Shared utility functions (utils.py)
These must exist before any spec is implemented:

```python
def notify_user(username: str, event: str, data: dict):
    socketio.emit(event, data, to=f"user_{username}")

def notify_admin(event: str, data: dict):
    socketio.emit(event, data, to='admin_room')

def get_patients_for_doctor(doctor_username: str) -> list[str]:
    ...

def get_doctor_for_patient(patient_username: str) -> str | None:
    ...

def insert_notification(username: str, type: str, message: str):
    db.execute("INSERT INTO notification (username, type, message) VALUES (?,?,?)",
               [username, type, message])
    db.commit()
```

## WebSocket events — complete reference

| Event | Direction | Payload |
|-------|-----------|---------|
| new_appointment | system → doctor | {appointment_id, patient_username, slot_date, slot_time, notes} |
| appointment_confirmed | system → patient | {appointment_id, slot_date, slot_time, doctor_username} |
| appointment_cancelled | system → other party | {appointment_id, cancelled_by} |
| new_report | system → patient | {prediction_id, doctor_username, risk_category, severity, anemia_type, hgb, date} |
| critical_alert | system → admin_room | {alert_id, patient_username, message, severity} |
| patient_alert | system → doctor | {alert_id, patient_username, message, severity} |
| my_alert | system → patient | {alert_id, message, severity} |
| alert_dismissed | system → admin_room | {alert_id} |
| new_message | system → recipient | {room_id, sender_username, content, created_at, attachment_url} |
| message_read | system → sender | {room_id} |
| typing | client → recipient | {room_id} |
| new_prescription | system → patient | {doctor_username, name, dose_mg, dose_unit, frequency, start_date} |
| medication_reminder | celery → patient | {med_id, message, scheduled_time} |
| low_adherence_alert | celery → doctor | {patient_username, med_name, adherence_pct} |
| assignment_update | system → doctor+patient | {doctor_username, patient_username} |
