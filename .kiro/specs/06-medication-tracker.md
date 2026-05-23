# Spec: Medication Tracker — Doctor Prescribes → Patient Tracks → System Reminds

## Overview
Medication must flow as a connected pipeline:
Doctor prescribes from the prediction result screen →
Patient receives it live in their tracker →
System sends reminders at scheduled times →
Doctor can monitor patient adherence.

This is NOT a standalone patient-only page.

## Dependencies
- Spec 01 (doctor_patient): prescriptions linked to assigned patients only
- Spec 02 (SocketContext): live prescription delivery
- Spec 04 (prediction pipeline): "Prescribe" button appears after CBC result

## Requirements

### 1. Database
```sql
CREATE TABLE medication (
  med_id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_username TEXT NOT NULL REFERENCES user(username),
  doctor_username TEXT REFERENCES user(username),
  prediction_id INTEGER,
  name TEXT NOT NULL,
  dose_mg REAL,
  dose_unit TEXT DEFAULT 'mg',
  frequency TEXT NOT NULL,  -- 'once_daily' | 'twice_daily' | 'three_times' | 'weekly'
  reminder_times TEXT,      -- JSON: ["08:00", "14:00"]
  start_date DATE NOT NULL,
  end_date DATE,
  notes TEXT,
  active INTEGER DEFAULT 1,
  added_by TEXT DEFAULT 'doctor'  -- 'doctor' | 'self'
);

CREATE TABLE medication_log (
  log_id INTEGER PRIMARY KEY AUTOINCREMENT,
  med_id INTEGER NOT NULL REFERENCES medication(med_id),
  scheduled_time TEXT NOT NULL,  -- "08:00"
  log_date DATE NOT NULL,
  action TEXT NOT NULL,  -- 'taken' | 'skipped'
  logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. Backend — blueprints/medication_bp.py (NEW FILE)

**POST /medications/prescribe**
- Doctor JWT required
- Body: `{patient_username, name, dose_mg, dose_unit, frequency, reminder_times, start_date, end_date, notes, prediction_id (optional)}`
- Validate: patient is assigned to current doctor
- Insert into medication table with doctor_username=current_user, added_by='doctor'
- Call `notify_user(patient_username, 'new_prescription', {doctor_username, name, dose_mg, dose_unit, frequency, start_date})`
- Insert notification for patient: "Dr. [name] prescribed [medication] [dose]"
- Schedule reminder tasks (see Celery section)
- Return: `{med_id}`

**POST /medications/self-add**
- Patient JWT required
- Body: `{name, dose_mg, dose_unit, frequency, reminder_times, start_date, notes}`
- Insert into medication with doctor_username=null, added_by='self'
- Schedule reminder tasks
- Return: `{med_id}`

**GET /medications/today**
- Patient JWT
- Return today's medications with taken/skipped status
- Logic: get all active medications for patient, calculate today's scheduled times, join with medication_log for today's date
- Response: `[{med_id, name, dose_mg, dose_unit, scheduled_time, action (null if not logged yet)}]`

**POST /medications/<id>/log**
- Patient JWT
- Body: `{action: 'taken'|'skipped', scheduled_time, log_date}`
- Validate: medication belongs to current patient
- Upsert into medication_log (if already logged for this time+date, update it)
- Return: `{logged: true}`

**GET /medications/my**
- Patient JWT
- Return all medications (active and completed) for current patient
- Include adherence % for each: taken_count / total_scheduled_days * 100

**GET /medications/adherence/<patient_username>**
- Doctor or Patient JWT
- If doctor: validate patient is assigned
- Return per-medication adherence for last 7 days and last 30 days
- Response: `[{med_id, name, last_7_days_pct, last_30_days_pct, total_taken, total_skipped}]`

**PUT /medications/<id>/deactivate**
- Doctor or Patient JWT
- Set active=0
- Return: `{deactivated: true}`

### 3. Celery tasks — tasks/reminder_tasks.py (NEW FILE)
```python
from celery import Celery
from celery.schedules import crontab

celery = Celery('tasks', broker='redis://localhost:6379/0')

@celery.task
def send_medication_reminder(med_id, patient_username, med_name, dose_mg, dose_unit):
    """Sends reminder notification to patient"""
    # Insert notification
    insert_notification(patient_username, 'medication_reminder',
        f"Time to take {med_name} {dose_mg}{dose_unit}")

    # Emit socket event
    notify_user(patient_username, 'medication_reminder', {
        'med_id': med_id,
        'message': f"Time to take {med_name} {dose_mg}{dose_unit}",
        'scheduled_time': datetime.now().strftime("%H:%M")
    })

    # Check 3-day adherence — alert doctor if low
    adherence = calculate_adherence(med_id, days=3)
    if adherence < 60:
        doctor = get_doctor_for_patient(patient_username)
        if doctor:
            notify_user(doctor, 'low_adherence_alert', {
                'patient_username': patient_username,
                'med_name': med_name,
                'adherence_pct': adherence
            })

def schedule_reminders_for_medication(med_id, patient_username, med_name, dose_mg, dose_unit, reminder_times):
    """Called when medication is prescribed or self-added"""
    import json
    times = json.loads(reminder_times) if isinstance(reminder_times, str) else reminder_times
    for time_str in times:
        hour, minute = map(int, time_str.split(':'))
        celery.conf.beat_schedule[f'med_{med_id}_{time_str}'] = {
            'task': 'tasks.reminder_tasks.send_medication_reminder',
            'schedule': crontab(hour=hour, minute=minute),
            'args': (med_id, patient_username, med_name, dose_mg, dose_unit)
        }
```

### 4. Frontend — PredictionResult.jsx (Doctor side) — ADD

After CBC result is displayed, add a "Prescribe Medication" button:

```jsx
<button onClick={() => setShowPrescribeModal(true)}>
  + Prescribe Medication
</button>

{showPrescribeModal && (
  <PrescriptionModal
    patientUsername={selectedPatient}
    predictionId={result.prediction_id}
    onClose={() => setShowPrescribeModal(false)}
    onSuccess={() => {
      setShowPrescribeModal(false);
      showToast("Prescription sent to patient");
    }}
  />
)}
```

**PrescriptionModal.jsx (NEW component):**
- Fields: Medicine Name (text), Dose (number + unit dropdown mg/ml/IU), Frequency (select), Reminder Times (time pickers, add/remove), Start Date, End Date, Notes
- "Prescribe" button: POST /medications/prescribe
- On success: close modal, show toast

### 5. Frontend — MedicationTracker.jsx (Patient side — NEW or replace existing)

**"Today" tab:**
- Fetch GET /medications/today on mount
- Show a card for each scheduled dose:
  ```
  [ 💊 Iron Tablet 100mg ]  08:00 AM
  [ ✓ Taken ] [ Skip ]
  ```
- "Taken" button: POST /medications/{id}/log with action='taken', turn green, disable both buttons
- "Skip" button: POST /medications/{id}/log with action='skipped', mark card grey
- Adherence streak banner: "🔥 5-day streak! Keep it up." (calculate from medication_log)

**"All Medications" tab:**
- List of all medications with active/completed badge
- Each row: name, dose, frequency, prescribed by, adherence %
- Progress bar showing adherence percentage
- "Deactivate" button for patient's self-added meds

**Socket event handling (addListener):**
- On 'new_prescription': add new card to today's list if reminder time is today, show toast "Dr. [name] prescribed [med]"
- On 'medication_reminder': show toast notification with "Mark Taken" action button in the toast

### 6. Frontend — PatientProfile.jsx (Doctor side — new component or tab in doctor dashboard)

When doctor clicks a patient name anywhere in the app, open their profile:
- Patient info: username, last CBC date, risk category
- "Medications" section: GET /medications/adherence/{patient_username}
  - Card per medication with 7-day adherence bar chart
  - Low adherence (< 60%) shown with red badge "⚠ Low Adherence"
- "Prescribe New" button opens PrescriptionModal

## Acceptance Criteria
- [ ] Doctor clicks "Prescribe" after CBC result → patient sees new medication appear in tracker live
- [ ] Medication reminder fires at the scheduled time each day
- [ ] Patient taps "Taken" → logged immediately, button turns green
- [ ] Doctor sees patient's adherence % broken down per medication
- [ ] If adherence < 60% for 3 days → doctor gets notified automatically
- [ ] Self-added medications also get reminders
- [ ] Completed (past end_date) medications move to "Completed" section
- [ ] Admin can see total prescriptions count in system stats
