# Spec: Doctor–Patient Assignment (BUILD THIS FIRST)

## Overview
This is the foundational relationship for the entire system. Every other feature
(appointments, messaging, alerts, CBC predictions, medication) depends on knowing
which doctor is assigned to which patient. Without this, all features are isolated pages.

## Requirements

### 1. Database
Create table `doctor_patient`:
- `assignment_id` INTEGER PRIMARY KEY AUTOINCREMENT
- `doctor_username` TEXT NOT NULL REFERENCES user(username)
- `patient_username` TEXT NOT NULL REFERENCES user(username)
- `assigned_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- `assigned_by` TEXT REFERENCES user(username)
- UNIQUE(doctor_username, patient_username)

### 2. Backend — admin_bp.py
Add these endpoints:

**GET /admin/unassigned-patients**
- Admin JWT required
- Returns all users with role='patient' who have no entry in doctor_patient table
- Response: `[{username, email, created_at}]`

**GET /admin/assignments**
- Admin JWT required
- Returns all rows from doctor_patient joined with user table
- Response: `[{doctor_username, patient_username, assigned_at, assigned_by}]`

**POST /admin/assign**
- Admin JWT required
- Body: `{doctor_username: string, patient_usernames: [string]}`
- Insert rows into doctor_patient for each patient
- After insert: emit SocketIO event `assignment_update` to room `user_{doctor_username}`
- After insert: emit SocketIO event `assignment_update` to each `user_{patient_username}`
- Response: `{assigned: number}`

**DELETE /admin/unassign**
- Admin JWT required
- Body: `{doctor_username: string, patient_username: string}`
- Delete row from doctor_patient
- Emit `assignment_update` to both affected users

### 3. Backend — shared utility (db.py or utils.py)
Add these two functions. Import them in EVERY other blueprint:

```python
def get_patients_for_doctor(doctor_username: str) -> list[str]:
    """Returns list of patient usernames assigned to this doctor"""
    rows = db.execute(
        "SELECT patient_username FROM doctor_patient WHERE doctor_username = ?",
        [doctor_username]
    ).fetchall()
    return [r['patient_username'] for r in rows]

def get_doctor_for_patient(patient_username: str) -> str | None:
    """Returns the doctor username assigned to this patient, or None"""
    row = db.execute(
        "SELECT doctor_username FROM doctor_patient WHERE patient_username = ?",
        [patient_username]
    ).fetchone()
    return row['doctor_username'] if row else None
```

### 4. Backend — new shared route (new file: blueprints/assignment_bp.py)

**GET /assignment/my-patients**
- Doctor JWT required
- Calls get_patients_for_doctor(current_user)
- Returns list of patient objects with username, email, last_prediction_date

**GET /assignment/my-doctor**
- Patient JWT required
- Calls get_doctor_for_patient(current_user)
- Returns doctor object: username, email, specialization

Register this blueprint in app.py.

### 5. Frontend — AdminDashboard.jsx
Add a new tab or section called "Assignments":

**AssignmentPanel.jsx** (new component):
- Left column: list of all doctors with their assigned patient count badge
- Right column (appears when doctor is clicked): 
  - List of currently assigned patients with an [X] remove button each
  - "Add Patient" button that opens a modal
- AddPatientModal.jsx:
  - Searchable list from GET /admin/unassigned-patients
  - Checkboxes to select multiple patients
  - "Assign" button calls POST /admin/assign
  - On success: close modal, refresh patient list without page reload

### 6. Frontend — Update ALL components to use assignment data

**CBCForm.jsx (Doctor side)**:
- Patient selector MUST call GET /assignment/my-patients
- Do NOT show all patients — only assigned ones
- If no patients assigned: show message "No patients assigned yet. Contact admin."

**PatientBooking.jsx / DoctorConnect (Patient side)**:
- MUST call GET /assignment/my-doctor to show their doctor
- If no doctor assigned: show message "You have not been assigned to a doctor yet."

**DoctorChat.jsx (Patient side)**:
- Conversation must be with their assigned doctor from GET /assignment/my-doctor

**AlertLog.jsx (Doctor side)**:
- Filter alerts using get_patients_for_doctor() — only their patients' alerts

**DoctorAppointments.jsx**:
- Only show appointments where doctor = current_user (not all appointments)

### 7. WebSocket
On `assignment_update` event received by frontend:
- Doctor: re-fetch GET /assignment/my-patients, update My Patients list live
- Patient: re-fetch GET /assignment/my-doctor, update Doctor Connect page live

## Acceptance Criteria
- [ ] Admin can assign a patient to a doctor from the dashboard
- [ ] Doctor's CBC form patient dropdown shows ONLY their assigned patients
- [ ] Patient's Doctor Connect page shows ONLY their assigned doctor
- [ ] If not assigned, both sides show a clear "not assigned" message (not a blank page)
- [ ] Unassigning a patient removes them from doctor's view immediately
- [ ] All other blueprints import and use get_patients_for_doctor() / get_doctor_for_patient()
