# Spec: CBC Prediction → Patient Report → Alert Pipeline

## Overview
When a doctor runs a CBC prediction, the result must:
1. Appear in the patient's report history automatically (live)
2. Update the patient's diet plan automatically
3. Trigger a critical alert if HGB is dangerously low (auto, no manual step)
4. Notify admin of critical cases in real time

## Dependencies
- Spec 01 (doctor_patient) must exist — doctor selects from assigned patients only
- Spec 02 (SocketContext) must exist — for live patient notification

## Requirements

### 1. Database — update prediction table
Add columns to existing prediction table:
```sql
ALTER TABLE prediction ADD COLUMN doctor_username TEXT REFERENCES user(username);
ALTER TABLE prediction ADD COLUMN clinical_notes TEXT;
ALTER TABLE prediction ADD COLUMN pdf_url TEXT;
```

### 2. Backend — predict_bp.py changes

**POST /predict — update existing endpoint:**

After saving prediction row, add this logic block:

```python
# Step 1: Save prediction (already done)
prediction_id = saved_row_id

# Step 2: Auto-create alerts based on HGB value
from services.alert_service import auto_create_alerts
auto_create_alerts(
    prediction_id=prediction_id,
    patient_username=target_patient,
    doctor_username=current_user,
    hgb=float(request.json['hgb']),
    risk_category=result['risk_category']
)

# Step 3: Notify patient in real time
from utils import notify_user
notify_user(target_patient, 'new_report', {
    'prediction_id': prediction_id,
    'doctor_username': current_user,
    'risk_category': result['risk_category'],
    'severity': result['severity'],
    'anemia_type': result['anemia_type'],
    'hgb': float(request.json['hgb']),
    'date': datetime.now().isoformat()
})

# Step 4: Insert notification for patient
insert_notification(target_patient, 'new_report',
    f"Dr. {current_user} added a new report. Risk: {result['risk_category']}")
```

**PUT /predict/<id>/notes — NEW endpoint:**
- Doctor JWT required
- Validate: prediction belongs to a patient assigned to current doctor
- Update clinical_notes field
- Return: `{saved: true}`

**GET /predict/patient/<username> — update existing:**
- Doctor JWT: validate patient is assigned to current doctor before returning data
- Patient JWT: only return own predictions
- Admin JWT: return all
- Include doctor_username in response so patient can see who ran it

### 3. Backend — alert_service.py — add auto_create_alerts()

```python
def auto_create_alerts(prediction_id, patient_username, doctor_username, hgb, risk_category):
    alerts_to_create = []

    if hgb < 8.0:
        alerts_to_create.append({
            'severity': 'critical',
            'message': f'Critical HGB detected: {hgb} g/dL for patient {patient_username}. Immediate attention required.',
        })
    elif hgb < 10.0:
        alerts_to_create.append({
            'severity': 'warning',
            'message': f'Low HGB detected: {hgb} g/dL for patient {patient_username}.',
        })

    if risk_category == 'High' and hgb >= 8.0:
        alerts_to_create.append({
            'severity': 'warning',
            'message': f'High anemia risk for patient {patient_username}. Review CBC values.',
        })

    for alert_data in alerts_to_create:
        # Save to alert table
        alert_id = db.execute(
            "INSERT INTO alert (patient_username, doctor_username, prediction_id, message, severity, triggered_by) VALUES (?,?,?,?,?,'system')",
            [patient_username, doctor_username, prediction_id, alert_data['message'], alert_data['severity']]
        ).lastrowid
        db.commit()

        payload = {
            'alert_id': alert_id,
            'patient_username': patient_username,
            'message': alert_data['message'],
            'severity': alert_data['severity'],
        }

        # Notify admin (all admins see critical + warning)
        notify_admin('critical_alert', payload)

        # Notify the doctor who ran the prediction
        notify_user(doctor_username, 'patient_alert', payload)

        # Notify the patient themselves (for dashboard banner)
        notify_user(patient_username, 'my_alert', payload)
```

### 4. Backend — alert table — update schema
```sql
ALTER TABLE alert ADD COLUMN doctor_username TEXT REFERENCES user(username);
ALTER TABLE alert ADD COLUMN prediction_id INTEGER REFERENCES prediction(patient_id);
ALTER TABLE alert ADD COLUMN triggered_by TEXT DEFAULT 'system';
ALTER TABLE alert ADD COLUMN dismissed_by TEXT;
ALTER TABLE alert ADD COLUMN dismissed_at TIMESTAMP;
```

**GET /alerts — update existing:**
- Admin JWT: return ALL alerts with patient_username, doctor_username, severity, dismissed
- Doctor JWT: return only alerts where doctor_username=current_user
- Patient JWT: return only alerts where patient_username=current_user

**PUT /alerts/<id>/dismiss:**
- Any role can dismiss their own visible alerts
- Set dismissed=TRUE, dismissed_by=current_user, dismissed_at=now()
- Notify admin room: `notify_admin('alert_dismissed', {alert_id})`

### 5. Frontend — CBCForm.jsx (Doctor side) — CHANGES

Replace any hardcoded patient field with a patient selector:

```jsx
// On mount: fetch assigned patients
const [patients, setPatients] = useState([]);
useEffect(() => {
  fetch('/assignment/my-patients', {headers: {Authorization: `Bearer ${token}`}})
    .then(r => r.json()).then(setPatients);
}, []);

// Render dropdown
<select onChange={e => setSelectedPatient(e.target.value)}>
  <option value="">Select patient...</option>
  {patients.map(p => <option key={p.username} value={p.username}>{p.username}</option>)}
</select>
```

After prediction result displays, show:
- "Add Clinical Notes" expandable textarea
- "Save Notes" button → PUT /predict/{id}/notes
- Result shows: Risk category, Severity, Anemia Type, SHAP explanation

### 6. Frontend — PatientDashboard.jsx — CHANGES

**ReportHistory.jsx:**
- Each row now shows: Date | Doctor | HGB | Risk | Severity | Anemia Type
- "Doctor" column shows who ran the test
- On 'new_report' socket event (via addListener): prepend new row to top of table, flash it green for 2 seconds

**DietRecommendations.jsx:**
- On 'new_report' socket event: re-fetch diet plan from backend
- Diet must update based on the latest anemia_type — not require page reload

**Critical Alert Banner:**
- On mount: fetch GET /alerts?dismissed=false for current patient
- If any severity='critical': show red full-width banner at top of dashboard
  "⚠ Critical result detected. Contact Dr. [doctor_username] immediately."
- Banner has "Message Doctor" button linking to messaging page
- On 'my_alert' socket event (severity=critical): show banner immediately without reload
- Banner dismisses when patient clicks "I understand" (calls PUT /alerts/{id}/dismiss)

### 7. Frontend — AdminDashboard.jsx — CHANGES

**AlertLog.jsx (Admin):**
- Show columns: Patient | Doctor | HGB Trigger | Message | Severity | Time | Status
- Color code rows: red=critical, amber=warning
- On 'critical_alert' socket event (via addListener): prepend row to top of table
- Severity filter buttons: All | Critical | Warning | Dismissed

**Reports Monitoring tab:**
- Add "Doctor" column to existing reports table
- Filter by doctor dropdown

## Acceptance Criteria
- [ ] Doctor selects patient from dropdown (only assigned patients shown)
- [ ] After prediction, patient sees new report appear in their history within 2 seconds
- [ ] Patient's diet plan updates automatically after new report (no reload)
- [ ] If HGB < 8.0: critical alert is created automatically with no manual step
- [ ] Doctor sees alert badge increment for their patient's critical result
- [ ] Admin sees critical alert appear in their panel live
- [ ] Patient sees critical banner on their dashboard for critical results
- [ ] Doctor can add clinical notes to a completed prediction
- [ ] All alerts show who triggered them and which patient they are for
