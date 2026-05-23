# Spec: Appointment Booking — Full Connected Flow

## Overview
Patient books → Doctor gets notified live → Doctor accepts/declines → Patient gets notified live.
Admin sees all bookings. This is NOT three separate pages. It is one connected pipeline.

## Dependencies
- Spec 01 (doctor_patient table) must exist
- Spec 02 (SocketContext) must exist
- Flask-Mail configured in app.py

## Requirements

### 1. Database
```sql
CREATE TABLE doctor_availability (
  availability_id INTEGER PRIMARY KEY AUTOINCREMENT,
  doctor_username TEXT NOT NULL REFERENCES user(username),
  day_of_week INTEGER NOT NULL,  -- 0=Monday, 6=Sunday
  start_time TEXT NOT NULL,      -- e.g. "09:00"
  end_time TEXT NOT NULL,        -- e.g. "17:00"
  slot_duration_minutes INTEGER DEFAULT 30
);

CREATE TABLE appointment (
  appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
  doctor_username TEXT NOT NULL REFERENCES user(username),
  patient_username TEXT NOT NULL REFERENCES user(username),
  slot_date DATE NOT NULL,
  slot_time TEXT NOT NULL,
  status TEXT DEFAULT 'pending',  -- pending | confirmed | cancelled | completed
  notes TEXT,
  cancelled_by TEXT,
  requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  confirmed_at TIMESTAMP
);
```

### 2. Backend — blueprints/appointments_bp.py (NEW FILE)

**GET /appointments/slots/<doctor_username>/<date>**
- No auth required (patient needs to see slots before booking)
- date format: YYYY-MM-DD
- Get doctor's availability for that day_of_week from doctor_availability table
- Generate all time slots between start_time and end_time at slot_duration_minutes intervals
- Remove slots that already exist in appointment table for that doctor+date with status != 'cancelled'
- Return: `{available_slots: ["09:00", "09:30", "10:00", ...]}`

**POST /appointments/request**
- Patient JWT required
- Body: `{doctor_username, slot_date, slot_time, notes}`
- Validate: patient is assigned to this doctor (check doctor_patient table) — return 403 if not
- Validate: slot is still available — return 409 if taken
- Insert into appointment table with status='pending'
- Call `notify_user(doctor_username, 'new_appointment', {...})` — from utils.py
- Call `notify_user(patient_username, 'appointment_request_sent', {...})`
- Send email to doctor via Flask-Mail
- Insert notification row for doctor
- Return: `{appointment_id, status: 'pending'}`

**PUT /appointments/<id>/confirm**
- Doctor JWT required
- Validate: this appointment belongs to current doctor — return 403 if not
- Update status='confirmed', confirmed_at=now()
- Call `notify_user(patient_username, 'appointment_confirmed', {appointment_id, slot_date, slot_time, doctor_username})`
- Send confirmation email to patient
- Insert notification for patient
- Return: `{status: 'confirmed'}`

**PUT /appointments/<id>/cancel**
- Doctor or Patient JWT
- Update status='cancelled', cancelled_by=current_user
- Call `notify_user(other_party, 'appointment_cancelled', {appointment_id, cancelled_by})`
- Insert notification for other party
- Return: `{status: 'cancelled'}`

**PUT /appointments/<id>/complete**
- Doctor JWT only
- Update status='completed'
- Return: `{status: 'completed'}`

**GET /appointments/my**
- Patient JWT: return own appointments ordered by slot_date DESC
- Doctor JWT: return all appointments where doctor_username=me, ordered by slot_date
- Admin JWT: return ALL appointments joined with user table (include doctor name, patient name)
- Always join with user table to include display names

**GET /appointments/pending-count**
- Doctor JWT: return count of appointments where doctor=me and status='pending'
- Used by Navbar badge on mount

**POST /appointments/availability**
- Doctor JWT required
- Body: `{day_of_week, start_time, end_time, slot_duration_minutes}`
- Insert or replace in doctor_availability
- Return: `{saved: true}`

**GET /appointments/availability/<doctor_username>**
- Return doctor's weekly availability schedule

### 3. Frontend — PatientBooking.jsx (replaces or extends DoctorConnect page)

Flow inside this component:
1. On mount: call GET /assignment/my-doctor to get assigned doctor
2. If no doctor: show "You have not been assigned to a doctor yet. Contact admin."
3. Show doctor info card (name, specialization)
4. Show date picker (only future dates)
5. On date select: call GET /appointments/slots/{doctor}/{date}
6. Show available time slots as clickable buttons (grey=available, disabled=taken)
7. "Notes for doctor" textarea
8. "Book Appointment" button: call POST /appointments/request
9. On success: show green toast "Appointment requested! Waiting for doctor confirmation."
10. Show upcoming appointments list below (from GET /appointments/my filtered to pending+confirmed)

Socket event handling (via useSocket addListener):
- On 'appointment_confirmed': find matching card in list, update status to "Confirmed ✓", show toast "Dr. [name] confirmed your appointment!"
- On 'appointment_cancelled' (by doctor): update card to "Cancelled", show toast

### 4. Frontend — DoctorAppointments.jsx (new component for DoctorDashboard)

Two tabs: "Pending Requests" and "Confirmed"

**Pending Requests tab:**
- List of appointment cards showing: patient name, requested date, time, notes
- Each card has [Confirm] button (green) and [Decline] button (red)
- [Confirm] calls PUT /appointments/{id}/confirm
- On success: remove card from Pending tab, add to Confirmed tab (no page reload)
- [Decline] calls PUT /appointments/{id}/cancel

**Confirmed tab:**
- Weekly calendar grid view
- Each confirmed appointment as a colored block in the grid
- Click a block to see patient details and a [Mark Complete] button

**On mount:**
- Subscribe to 'new_appointment' via addListener
- On 'new_appointment' event: prepend new card to Pending tab, show toast "New appointment request from [patient]"
- On unmount: removeListener

**Availability Settings (collapsible panel):**
- For each day of week: toggle on/off, set start time, end time
- "Save Availability" button calls POST /appointments/availability

### 5. Frontend — AdminAppointments.jsx (tab in AdminDashboard)

- Stats row: Total Today | Pending | Confirmed | Cancelled
- Table: Patient Name | Doctor Name | Date | Time | Status | Requested At
- Filter buttons: All | Pending | Confirmed | Cancelled | Completed
- No actions needed for admin — view only

### 6. Frontend — PatientDashboard.jsx
Add "Upcoming Appointment" card to the dashboard home:
- Call GET /appointments/my, take the first confirmed future appointment
- Show: "Your next appointment is with Dr. [name] on [date] at [time]"
- If none: show "No upcoming appointments. Book one with your doctor."
- Link to PatientBooking page

## Acceptance Criteria
- [ ] Patient books appointment → doctor sees it appear live without refresh
- [ ] Doctor confirms → patient sees "Confirmed" status update live without refresh
- [ ] Doctor declines → patient sees "Cancelled" status update live without refresh  
- [ ] Email sent to doctor on new request
- [ ] Email sent to patient on confirmation
- [ ] Doctor cannot see appointments of patients not assigned to them
- [ ] Patient cannot book with a doctor they are not assigned to (403 error)
- [ ] Time slots that are already booked do not appear as available
- [ ] Admin can see all appointments with both names
- [ ] Appointment count badge on doctor Navbar updates live
