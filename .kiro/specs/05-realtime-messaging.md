# Spec: Doctor–Patient Real-Time Messaging

## Overview
A direct messaging channel between an assigned doctor and patient.
Messages appear live on both sides without any page refresh.
This is SEPARATE from the Gemini AI chatbot — keep the AI chatbot as "AI Health Assistant".
This is "Message My Doctor" — real human-to-human communication.

## Dependencies
- Spec 01 (doctor_patient): needed to know who can message whom
- Spec 02 (SocketContext): needed for live message delivery

## Requirements

### 1. Database
```sql
CREATE TABLE chat_room (
  room_id INTEGER PRIMARY KEY AUTOINCREMENT,
  doctor_username TEXT NOT NULL REFERENCES user(username),
  patient_username TEXT NOT NULL REFERENCES user(username),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_message_at TIMESTAMP,
  UNIQUE(doctor_username, patient_username)
);

CREATE TABLE chat_message (
  message_id INTEGER PRIMARY KEY AUTOINCREMENT,
  room_id INTEGER NOT NULL REFERENCES chat_room(room_id),
  sender_username TEXT NOT NULL REFERENCES user(username),
  content TEXT,
  attachment_url TEXT,
  attachment_type TEXT,  -- 'pdf' | 'image' | null
  is_read INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. Backend — blueprints/messaging_bp.py (NEW FILE)

**GET /messages/room/<patient_username>**
- Doctor or Patient JWT
- If doctor: validate patient is in their assigned list
- If patient: validate doctor_username is their assigned doctor
- Get or create chat_room for this (doctor, patient) pair
- Mark all messages from the OTHER party as is_read=1
- Return last 50 messages ordered by created_at ASC (oldest first for display)
- Response: `{room_id, messages: [{message_id, sender_username, content, attachment_url, attachment_type, is_read, created_at}]}`

**POST /messages/send**
- Doctor or Patient JWT
- Body: `{room_id, content, attachment_url (optional), attachment_type (optional)}`
- Insert into chat_message
- Get the recipient username from the room (if sender=doctor, recipient=patient and vice versa)
- Call `notify_user(recipient_username, 'new_message', {room_id, sender_username, content, created_at, attachment_url, attachment_type})`
- Update chat_room.last_message_at = now()
- Return: `{message_id, created_at}`

**GET /messages/unread-count**
- Doctor or Patient JWT
- Count of messages where recipient is current user and is_read=0
- "Recipient" means: if current_user is doctor, count messages in their rooms sent by patients that are unread
- Return: `{count: number}`

**GET /messages/rooms**
- Doctor JWT only
- Return all chat rooms for this doctor with last message preview and unread count per room
- Response: `[{room_id, patient_username, last_message, last_message_at, unread_count}]`

**POST /messages/upload**
- Doctor or Patient JWT
- Accept multipart/form-data with file field
- Accept: PDF (max 5MB), images (max 2MB)
- Save to /uploads/chat/{uuid}_{filename}
- Return: `{url, attachment_type}`

**POST /messages/mark-read**
- Body: `{room_id}`
- Mark all messages in room from other party as is_read=1
- Emit `message_read` event to other party: `notify_user(sender, 'message_read', {room_id})`

### 3. Backend — Flask-SocketIO event in app.py
```python
@socketio.on('typing')
def on_typing(data):
    # data = {room_id, recipient_username}
    emit('typing', {'room_id': data['room_id']}, to=f"user_{data['recipient_username']}")
```

### 4. Frontend — DoctorChat.jsx (NEW component)

This component is used in BOTH DoctorDashboard and PatientDashboard but renders differently by role.

**Layout:**
```
[Left sidebar: conversation list] | [Right: message thread]
```

**For Patient (only one conversation — their assigned doctor):**
- No sidebar needed — goes straight to the message thread
- Header: "Dr. [doctor_username]" with online indicator dot
- Message thread: messages ordered oldest to newest
  - Own messages: right-aligned, blue bubble
  - Doctor messages: left-aligned, grey bubble
  - Timestamp shown below each bubble
  - PDF attachment: download card with PDF icon and filename
  - Image attachment: inline preview, click to enlarge
- Typing indicator: "Dr. [name] is typing..." with animated dots
- Input bar at bottom: text input + paperclip (attachment) + send button
- On send: POST /messages/send, append message to thread immediately (optimistic update)
- On 'new_message' socket event (addListener): append incoming message to thread
- On 'typing' socket event: show typing indicator, hide after 3 seconds

**For Doctor (multiple conversations):**
- Left sidebar: list of patients from GET /messages/rooms
  - Each item: patient name, last message preview, time, unread badge
  - Click to open that room
- Right panel: same message thread as patient view
- On 'new_message' event: if room is open → append to thread; if not → increment sidebar unread badge

**Shared behavior:**
- On component mount: call GET /messages/room/{patient} to load history, mark as read
- On text input change: emit 'typing' socket event (debounced 500ms)
- On attachment button: open file picker, call POST /messages/upload, then include url in send
- Messages sent during disconnection: queue locally, resend on reconnect

### 5. Frontend — PatientDashboard.jsx
Replace "Message your AI assistant" or add below it:
- "Message My Doctor" card with button linking to DoctorChat
- Show last message preview and time if conversation exists
- Show unread count badge on the card

### 6. Frontend — DoctorDashboard.jsx
Add "Messages" section or tab:
- List of patient conversations with unread counts from GET /messages/rooms
- Click to open DoctorChat with that patient
- Unread badge in Navbar updates via SocketContext

## Acceptance Criteria
- [ ] Patient sends message → doctor sees it appear within 1 second without refresh
- [ ] Doctor replies → patient sees it appear within 1 second without refresh
- [ ] Typing indicator appears when other party is typing
- [ ] Unread message count badge in Navbar updates globally (not just on messages page)
- [ ] Doctor can attach a PDF (CBC report) — patient can download it
- [ ] Message history persists across page reloads
- [ ] Patient can only message their assigned doctor
- [ ] Doctor can only message their assigned patients
- [ ] Admin cannot read individual messages (privacy)
