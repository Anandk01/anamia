# Design Document: AnemiaCare Production Upgrade

## Overview

The AnemiaCare Production Upgrade transforms the existing anemia detection prototype into a production-grade clinical platform. The current system provides ML-based anemia prediction with basic RBAC, but lacks critical cross-role workflows (doctor-patient relationships, appointments, prescriptions), real-time communication, medication tracking, community features, and production infrastructure (PostgreSQL, WebSocket, task queues).

This upgrade addresses 12 major capability gaps identified during production readiness review. The architecture migrates from SQLite to PostgreSQL with SQLAlchemy ORM, adds Flask-SocketIO for real-time messaging, introduces Celery+Redis for background job scheduling, and expands the frontend with PWA support, dark mode, and accessibility compliance. The ML pipeline gains proper evaluation with real datasets, additional models (XGBoost, LightGBM), and drift detection.

Priority ordering ensures the most visible gaps (doctor-patient workflow, appointments) ship first, followed by medication tracking, ML improvements, real-time messaging, community features, infrastructure upgrades, and frontend polish.

---

## Architecture

### System Architecture (Post-Upgrade)

```mermaid
graph TD
    subgraph Frontend["React 19 + Vite + Tailwind (PWA)"]
        UI[UI Components]
        SW[Service Worker]
        WS_CLIENT[WebSocket Client]
    end

    subgraph API["Flask REST API + SocketIO"]
        BLUEPRINTS[12 Blueprints]
        SOCKETIO[Flask-SocketIO]
        MIDDLEWARE[JWT + RBAC + Audit]
        ORM[SQLAlchemy ORM]
    end

    subgraph Workers["Background Workers"]
        CELERY[Celery Workers]
        BEAT[Celery Beat Scheduler]
    end

    subgraph Data["Data Layer"]
        PG[(PostgreSQL)]
        REDIS[(Redis)]
        S3[File Storage]
    end

    subgraph ML["ML Pipeline"]
        MODELS[RF + GB + XGBoost + LightGBM]
        EVAL[Evaluation Engine]
        DRIFT[Drift Detector]
        SHAP_ENGINE[SHAP Explainer]
    end

    subgraph External["External Services"]
        GEMINI[Google Gemini API]
        SMTP[SMTP Email]
        PUSH[Web Push API]
    end

    UI -->|HTTP/JSON| BLUEPRINTS
    WS_CLIENT -->|WebSocket| SOCKETIO
    SW -->|Push| PUSH
    BLUEPRINTS --> MIDDLEWARE
    MIDDLEWARE --> ORM
    ORM --> PG
    SOCKETIO --> REDIS
    CELERY --> PG
    CELERY --> REDIS
    CELERY --> SMTP
    CELERY --> PUSH
    BEAT --> CELERY
    BLUEPRINTS --> MODELS
    BLUEPRINTS --> GEMINI
    EVAL --> PG
    DRIFT --> PG
```

### Deployment Architecture

```mermaid
graph LR
    subgraph Client
        BROWSER[Browser/PWA]
    end

    subgraph Server["Application Server"]
        FLASK[Flask + Gunicorn]
        SOCKETIO_SRV[SocketIO Server]
    end

    subgraph Background
        CELERY_W[Celery Worker x2]
        CELERY_B[Celery Beat]
    end

    subgraph Persistence
        POSTGRES[(PostgreSQL 15)]
        REDIS_CACHE[(Redis 7)]
    end

    BROWSER --> FLASK
    BROWSER --> SOCKETIO_SRV
    FLASK --> POSTGRES
    FLASK --> REDIS_CACHE
    SOCKETIO_SRV --> REDIS_CACHE
    CELERY_W --> POSTGRES
    CELERY_W --> REDIS_CACHE
    CELERY_B --> REDIS_CACHE
```

---

## Sequence Diagrams

### Doctor-Patient Assignment Flow

```mermaid
sequenceDiagram
    participant D as Doctor
    participant API as Flask API
    participant DB as PostgreSQL
    participant N as Notification Service

    D->>API: POST /api/doctors/patients/assign {patient_id}
    API->>API: Validate JWT + role=doctor
    API->>DB: Check patient exists & not already assigned
    DB-->>API: Patient record
    API->>DB: INSERT INTO doctor_patient (doctor_id, patient_id)
    DB-->>API: Success
    API->>N: Queue assignment notification
    N-->>API: Queued
    API-->>D: 201 {assignment_id, patient_info}
```

### Appointment Booking Flow

```mermaid
sequenceDiagram
    participant P as Patient
    participant API as Flask API
    participant DB as PostgreSQL
    participant D as Doctor
    participant N as Notification Service

    P->>API: POST /api/appointments/request {doctor_id, slot_date, slot_time, notes}
    API->>API: Validate JWT + role=patient
    API->>DB: Check doctor_patient relationship exists
    DB-->>API: Relationship confirmed
    API->>DB: Check slot availability
    DB-->>API: Slot available
    API->>DB: INSERT appointment (status=pending)
    DB-->>API: appointment_id
    API->>N: Notify doctor of new request
    API-->>P: 201 {appointment_id, status: pending}

    D->>API: PUT /api/appointments/{id}/confirm
    API->>DB: UPDATE appointment SET status=confirmed
    API->>N: Notify patient of confirmation
    API-->>D: 200 {appointment updated}
```

### Real-Time Messaging Flow

```mermaid
sequenceDiagram
    participant D as Doctor Client
    participant SIO as Flask-SocketIO
    participant REDIS as Redis PubSub
    participant DB as PostgreSQL
    participant P as Patient Client

    D->>SIO: connect(token)
    SIO->>SIO: Authenticate JWT
    SIO-->>D: connected

    P->>SIO: connect(token)
    SIO-->>P: connected

    P->>SIO: emit("join_room", {doctor_id})
    SIO->>DB: Verify doctor_patient relationship
    SIO->>REDIS: Subscribe to room channel
    SIO-->>P: room_joined

    P->>SIO: emit("send_message", {room_id, content, type})
    SIO->>DB: INSERT INTO message (room_id, sender, content)
    SIO->>REDIS: Publish to room channel
    REDIS-->>SIO: Broadcast
    SIO-->>D: emit("new_message", {message_data})
    SIO-->>P: emit("message_sent", {message_id})

    D->>SIO: emit("message_read", {message_id})
    SIO->>DB: UPDATE message SET read_at=now()
    SIO-->>P: emit("read_receipt", {message_id})
```

### Medication Adherence Tracking Flow

```mermaid
sequenceDiagram
    participant P as Patient
    participant API as Flask API
    participant DB as PostgreSQL
    participant CELERY as Celery Worker
    participant PUSH as Push Service

    Note over CELERY: Daily at configured time
    CELERY->>DB: SELECT active medications for today
    DB-->>CELERY: medication list
    CELERY->>PUSH: Send reminder notifications
    PUSH-->>P: "Time to take Iron Supplement (65mg)"

    P->>API: POST /api/medications/{med_id}/log {taken: true}
    API->>DB: INSERT INTO medication_log (med_id, taken_at)
    API-->>P: 201 {log_id, streak_count}

    P->>API: GET /api/medications/adherence
    API->>DB: Calculate 7-day adherence percentage
    DB-->>API: {adherence: 85.7, streak: 5, missed: 1}
    API-->>P: 200 {adherence_data}
```

---

## Components and Interfaces

### New Backend Blueprints
