# Requirements Document

## Introduction

This document defines the requirements for a comprehensive Anemia Detection and Management System built on top of the existing Flask/React/SQLite stack. The system extends the current CBC risk-classification and symptom-triage prototype into a full clinical decision-support platform. It adds ML-powered anemia prediction (presence, severity, and type), explainable AI, personalised diet and health recommendations, automated doctor alerts, patient self-service (login, history, Hb trend charts, PDF reports), OCR-based blood-report ingestion, a conversational chatbot, multi-language support, an admin monitoring dashboard, and a model-retraining pipeline.

---

## Glossary

- **System**: The Anemia Detection and Management System as a whole.
- **Prediction_Engine**: The ML subsystem responsible for anemia detection, severity classification, and type classification.
- **Explainability_Module**: The component that generates human-readable reasons for each prediction (e.g., SHAP values or rule-based explanations).
- **Recommendation_Engine**: The component that produces diet plans and personalised health tips based on prediction results.
- **Alert_Service**: The component that sends notifications to doctors when a patient's result meets critical thresholds.
- **Patient**: A registered end-user who submits blood test data and views their own results. Assigned the role value `"patient"`.
- **Doctor**: A clinical user who reviews patient results, receives alerts, and manages patient records. Assigned the role value `"doctor"`.
- **Admin**: A privileged user who monitors system usage, manages user accounts, and triggers model retraining. Assigned the role value `"admin"`.
- **RBAC**: Role-Based Access Control — the permission model that maps each role to a defined set of allowed and forbidden actions.
- **Access_Violation_Log**: A persistent audit log that records every 403 Forbidden response, including the requesting username, endpoint, role claim, and timestamp.
- **OCR_Service**: The component that extracts structured CBC values from uploaded blood-report images or PDFs.
- **Chatbot**: The conversational interface that answers basic anemia-related queries.
- **Report_Generator**: The component that produces downloadable PDF summaries of a patient's prediction result.
- **Trend_Tracker**: The component that stores and visualises a patient's Hb (haemoglobin) values over time.
- **Retraining_Pipeline**: The backend workflow that retrains ML models with newly labelled data.
- **CBC**: Complete Blood Count — a standard blood panel including RBC, MCV, MCH, MCHC, RDW, TLC, PLT, and HGB values.
- **HGB**: Haemoglobin concentration in g/dL, the primary indicator used for anemia severity thresholds.
- **Severity_Level**: One of three ordered categories — Mild, Moderate, or Severe — assigned based on HGB thresholds and model output.
- **Anemia_Type**: One of the supported anemia sub-types: Iron-Deficiency, Vitamin B12 Deficiency, Folate Deficiency, or Other.
- **Critical_Threshold**: An HGB value below 7.0 g/dL or a Severity_Level of Severe, which triggers an automatic doctor alert.
- **OTP**: One-time password sent via email for identity verification during registration and password reset.
- **JWT**: JSON Web Token used for stateless session authentication.
- **Supported_Languages**: English, Hindi, Tamil, and any additional languages configured by the Admin.

---

## Requirements

### Requirement 1: Anemia Presence Prediction

**User Story:** As a Doctor, I want the system to predict whether a patient has anemia from their CBC values, so that I can make faster, data-driven clinical decisions.

#### Acceptance Criteria

1. WHEN a Doctor submits a valid set of CBC values (RBC, MCV, MCH, MCHC, RDW, TLC, PLT, HGB), THE Prediction_Engine SHALL return a binary anemia prediction of either "Anemia Detected" or "No Anemia Detected".
2. THE Prediction_Engine SHALL produce a prediction within 2 seconds of receiving a valid CBC input under normal load.
3. IF any required CBC field is missing or contains a non-numeric value, THEN THE Prediction_Engine SHALL return a descriptive validation error identifying each invalid field.
4. THE Prediction_Engine SHALL achieve a minimum classification accuracy of 85% on the held-out test split of the training dataset.
5. WHEN a prediction is produced, THE System SHALL persist the prediction result alongside the input CBC values and the submitting Doctor's username in the database.

---

### Requirement 2: Severity Detection

**User Story:** As a Doctor, I want the system to classify the severity of detected anemia, so that I can prioritise treatment urgency appropriately.

#### Acceptance Criteria

1. WHEN the Prediction_Engine returns "Anemia Detected", THE Prediction_Engine SHALL also return a Severity_Level of Mild, Moderate, or Severe.
2. THE Prediction_Engine SHALL assign Severity_Level according to the following HGB-based thresholds for adults: Mild when HGB is between 10.0 and 11.9 g/dL, Moderate when HGB is between 8.0 and 9.9 g/dL, and Severe when HGB is below 8.0 g/dL.
3. WHEN the Prediction_Engine returns "No Anemia Detected", THE Prediction_Engine SHALL return a Severity_Level of "None".
4. THE System SHALL display the Severity_Level alongside a colour-coded indicator: green for None, yellow for Mild, orange for Moderate, and red for Severe.

---

### Requirement 3: Anemia Type Prediction

**User Story:** As a Doctor, I want the system to predict the likely type of anemia, so that I can guide targeted treatment without waiting for additional specialist tests.

#### Acceptance Criteria

1. WHEN the Prediction_Engine returns "Anemia Detected", THE Prediction_Engine SHALL also return a predicted Anemia_Type from the set: Iron-Deficiency, Vitamin B12 Deficiency, Folate Deficiency, or Other.
2. THE Prediction_Engine SHALL return a confidence score between 0.0 and 1.0 for the predicted Anemia_Type.
3. WHEN the Prediction_Engine returns "No Anemia Detected", THE Prediction_Engine SHALL return an Anemia_Type of "N/A".
4. THE System SHALL display the predicted Anemia_Type and its confidence score to the Doctor on the result screen.

---

### Requirement 4: Explainable AI Results

**User Story:** As a Doctor, I want to see the reasons behind each prediction, so that I can validate the model's output against my clinical knowledge.

#### Acceptance Criteria

1. WHEN a prediction is produced, THE Explainability_Module SHALL generate a human-readable explanation listing the top 3 CBC features that most influenced the prediction result.
2. THE Explainability_Module SHALL express each feature's contribution as a directional statement (e.g., "Low HGB strongly indicates anemia").
3. THE System SHALL display the explanation alongside the prediction result without requiring an additional user action.
4. IF the Explainability_Module fails to generate an explanation, THEN THE System SHALL display the prediction result without an explanation and log the failure internally.

---

### Requirement 5: Diet Recommendations

**User Story:** As a Patient, I want to receive diet recommendations based on my anemia result, so that I can take immediate dietary steps to improve my condition.

#### Acceptance Criteria

1. WHEN a prediction result is produced, THE Recommendation_Engine SHALL generate a diet recommendation specific to the predicted Anemia_Type.
2. THE Recommendation_Engine SHALL include at least 5 food items per recommendation, each with a brief rationale (e.g., "Spinach — high in non-haem iron").
3. WHEN the prediction result is "No Anemia Detected", THE Recommendation_Engine SHALL return a general iron-maintenance diet recommendation.
4. THE System SHALL display diet recommendations on the result screen and include them in the PDF report.
5. WHERE a Patient's profile includes dietary restrictions (e.g., vegan), THE Recommendation_Engine SHALL filter out non-compliant food items from the recommendation list.

---

### Requirement 6: Doctor Alerts for Critical Cases

**User Story:** As a Doctor, I want to receive an automatic alert when a patient's result meets the Critical_Threshold, so that I can act immediately without manually reviewing every result.

#### Acceptance Criteria

1. WHEN a prediction result meets the Critical_Threshold (HGB below 7.0 g/dL or Severity_Level of Severe), THE Alert_Service SHALL send an email notification to the Doctor associated with the submission within 60 seconds.
2. THE Alert_Service SHALL include the patient's username, the HGB value, the Severity_Level, and the timestamp in the alert email.
3. IF the Alert_Service fails to deliver the email, THEN THE Alert_Service SHALL retry delivery up to 3 times at 30-second intervals and log each failed attempt.
4. THE System SHALL record every alert sent in the database, including the recipient, timestamp, and delivery status.
5. THE Admin SHALL be able to view the alert log from the Admin dashboard.

---

### Requirement 7: Personalised Health Tips

**User Story:** As a Patient, I want to receive personalised health tips based on my result, so that I can make lifestyle changes that complement my treatment.

#### Acceptance Criteria

1. WHEN a prediction result is produced, THE Recommendation_Engine SHALL generate at least 3 personalised health tips relevant to the patient's Severity_Level and Anemia_Type.
2. WHEN the patient's profile includes age and sex, THE Recommendation_Engine SHALL tailor health tips to those demographic attributes.
3. THE System SHALL display health tips on the result screen below the diet recommendations.
4. THE System SHALL include health tips in the PDF report.

---

### Requirement 8: Patient Registration and Login

**User Story:** As a Patient, I want to register and log in to the system, so that I can securely access my personal health records.

#### Acceptance Criteria

1. WHEN a new user submits a registration form with a unique username, a valid email address, and a password of at least 8 characters, THE System SHALL send a 6-digit OTP to the provided email address within 60 seconds.
2. WHEN the user submits the correct OTP within 10 minutes of issuance, THE System SHALL create the account and assign the role of "patient".
3. IF the OTP submitted during registration is incorrect or expired, THEN THE System SHALL return a descriptive error and allow the user to request a new OTP.
4. WHEN a registered user submits valid credentials, THE System SHALL issue a JWT with an expiry of 24 hours and redirect the user to their dashboard.
5. IF a login attempt is made with invalid credentials, THEN THE System SHALL return an error message and increment a failed-attempt counter for that account.
6. WHEN a user's failed-attempt counter reaches 5 within a 15-minute window, THE System SHALL lock the account for 15 minutes and notify the user via email.
7. WHEN a logged-in user requests logout, THE System SHALL invalidate the JWT and redirect the user to the login page.
8. THE System SHALL support password reset via OTP sent to the registered email address, following the same OTP flow as registration.

---

### Requirement 9: Previous Report History

**User Story:** As a Patient, I want to view my previous prediction reports, so that I can track my health over time and share records with my doctor.

#### Acceptance Criteria

1. WHEN a logged-in Patient navigates to the History section, THE System SHALL display all previous prediction records associated with that Patient's account, ordered by date descending.
2. THE System SHALL display for each record: the submission date, CBC values, anemia prediction, Severity_Level, Anemia_Type, and the top explanation feature.
3. WHEN a Patient selects a specific record, THE System SHALL display the full result detail including diet recommendations and health tips for that record.
4. THE System SHALL paginate the history list at 20 records per page.
5. IF a Patient has no previous records, THEN THE System SHALL display an empty-state message prompting the Patient to submit their first CBC test.

---

### Requirement 10: Hb Trend Charts and Progress Tracking

**User Story:** As a Patient, I want to see a chart of my HGB values over time, so that I can visually monitor whether my condition is improving.

#### Acceptance Criteria

1. WHEN a logged-in Patient navigates to the Progress section, THE Trend_Tracker SHALL render a line chart of the Patient's HGB values plotted against submission dates.
2. THE Trend_Tracker SHALL display at least the most recent 12 data points on the chart.
3. THE Trend_Tracker SHALL overlay horizontal reference lines on the chart at the Mild (11.9 g/dL), Moderate (9.9 g/dL), and Severe (8.0 g/dL) severity thresholds.
4. WHEN a Patient hovers over a data point, THE Trend_Tracker SHALL display a tooltip showing the exact HGB value, date, and Severity_Level for that submission.
5. IF a Patient has fewer than 2 data points, THEN THE Trend_Tracker SHALL display an informational message explaining that at least 2 submissions are needed to show a trend.

---

### Requirement 11: PDF Report Generation

**User Story:** As a Patient or Doctor, I want to download a PDF summary of a prediction result, so that I can share it with other healthcare providers or keep it for personal records.

#### Acceptance Criteria

1. WHEN a user clicks "Download PDF" on a result or history record, THE Report_Generator SHALL produce a PDF file within 5 seconds.
2. THE Report_Generator SHALL include in the PDF: the patient's name, submission date, CBC values table, anemia prediction, Severity_Level, Anemia_Type, confidence score, top 3 explanation features, diet recommendations, and health tips.
3. THE Report_Generator SHALL format the PDF with the system's branding (logo, colour scheme) and a footer containing the generation timestamp and a disclaimer that the report is not a substitute for professional medical advice.
4. THE Report_Generator SHALL name the downloaded file using the pattern `anemia_report_{username}_{YYYYMMDD}.pdf`.
5. IF the PDF generation fails, THEN THE System SHALL display an error message and offer the user a retry option.

---

### Requirement 12: OCR Blood Report Ingestion

**User Story:** As a Patient or Doctor, I want to upload a scanned blood report image or PDF and have the CBC values extracted automatically, so that I do not have to enter values manually.

#### Acceptance Criteria

1. WHEN a user uploads a blood report file in JPEG, PNG, or PDF format with a maximum size of 10 MB, THE OCR_Service SHALL extract the CBC values (RBC, MCV, MCH, MCHC, RDW, TLC, PLT, HGB) from the file.
2. THE OCR_Service SHALL pre-populate the CBC input form with the extracted values within 10 seconds of upload.
3. THE System SHALL display each extracted value alongside a confidence indicator (High, Medium, or Low) so the user can verify accuracy before submission.
4. IF the OCR_Service cannot extract one or more CBC values, THEN THE System SHALL leave those fields empty and display a warning identifying the unextracted fields.
5. IF the uploaded file exceeds 10 MB or is not in a supported format, THEN THE System SHALL reject the upload and display a descriptive error message before any processing occurs.
6. THE OCR_Service SHALL NOT store the uploaded file permanently; THE OCR_Service SHALL delete the file from temporary storage within 60 seconds of extraction completion.

---

### Requirement 13: Anemia Chatbot

**User Story:** As a Patient, I want to ask basic questions about anemia through a chat interface, so that I can get quick answers without leaving the application.

#### Acceptance Criteria

1. WHEN a Patient submits a text query through the Chatbot interface, THE Chatbot SHALL return a relevant response within 3 seconds.
2. THE Chatbot SHALL correctly answer queries covering at least the following topics: anemia definition, common symptoms, anemia types, dietary advice, when to see a doctor, and how to interpret CBC values.
3. WHEN a Patient asks a question outside the Chatbot's knowledge domain, THE Chatbot SHALL respond with a polite out-of-scope message and suggest consulting a doctor.
4. THE Chatbot SHALL maintain conversation context for at least the 5 most recent message exchanges within a single session.
5. THE Chatbot SHALL NOT provide specific medical diagnoses or prescribe medication; IF such a query is detected, THEN THE Chatbot SHALL redirect the Patient to consult a qualified doctor.

---

### Requirement 14: Multi-Language Support

**User Story:** As a Patient, I want to use the application in my preferred language, so that I can understand my results and recommendations without a language barrier.

#### Acceptance Criteria

1. THE System SHALL support at least the following Supported_Languages: English, Hindi, and Tamil.
2. WHEN a user selects a language from the language selector, THE System SHALL render all UI labels, error messages, diet recommendations, health tips, and chatbot responses in the selected language within 500 milliseconds.
3. THE System SHALL persist the user's language preference in their profile so that it is applied automatically on subsequent logins.
4. WHERE a translation for a UI string is unavailable in the selected language, THE System SHALL fall back to English and log the missing translation key.
5. THE Report_Generator SHALL generate PDF reports in the language selected by the user at the time of download.

---

### Requirement 15: Admin Dashboard for Usage Monitoring

**User Story:** As an Admin, I want a dashboard that shows system usage statistics and user activity, so that I can monitor system health and identify usage patterns.

#### Acceptance Criteria

1. WHEN an Admin logs in, THE System SHALL display the Admin Dashboard as the default landing page.
2. THE Admin Dashboard SHALL display the following real-time metrics: total registered patients, total CBC predictions performed, total triage assessments performed, count of predictions by Severity_Level, count of predictions by Anemia_Type, and count of critical alerts sent.
3. THE Admin Dashboard SHALL render a time-series chart showing the number of predictions per day for the most recent 30 days.
4. THE Admin Dashboard SHALL allow the Admin to search, filter, and view all user accounts by username, email, and role.
5. THE Admin Dashboard SHALL allow the Admin to create new user accounts and deactivate existing non-admin accounts.
6. THE Admin Dashboard SHALL display the alert log with columns for recipient, patient username, alert timestamp, and delivery status.
7. WHEN the Admin refreshes the dashboard, THE System SHALL reload all metrics within 3 seconds.

---

### Requirement 16: Model Retraining Pipeline

**User Story:** As an Admin, I want to retrain the ML models with new labelled data, so that the system's prediction accuracy improves as more clinical data becomes available.

#### Acceptance Criteria

1. WHEN an Admin uploads a CSV file containing new labelled training data through the Admin Dashboard, THE Retraining_Pipeline SHALL validate that the file contains the required columns (RBC, MCV, MCH, MCHC, RDW, TLC, PLT, HGB, and a label column) before beginning retraining.
2. IF the uploaded CSV is missing required columns or contains non-numeric values in feature columns, THEN THE Retraining_Pipeline SHALL reject the file and return a descriptive error identifying each invalid column.
3. WHEN the Admin initiates retraining, THE Retraining_Pipeline SHALL train the new model on the combined existing and uploaded data and evaluate it against a held-out validation split.
4. THE Retraining_Pipeline SHALL display the new model's accuracy, precision, recall, and F1-score to the Admin before the model is deployed.
5. WHEN the Admin approves the new model, THE Retraining_Pipeline SHALL replace the active model files and reload the Prediction_Engine without requiring a server restart.
6. IF the new model's accuracy is more than 5 percentage points lower than the currently deployed model's accuracy, THEN THE Retraining_Pipeline SHALL warn the Admin and require explicit confirmation before deployment.
7. THE Retraining_Pipeline SHALL retain the previous model files as a backup so that the Admin can roll back to the prior version.
8. THE System SHALL log each retraining event with the timestamp, the Admin's username, the dataset size, and the resulting model metrics.

---

### Requirement 17: Secure Authentication and Session Management

**User Story:** As a system operator, I want all user sessions to be secured with token-based authentication, so that patient data is protected from unauthorised access.

#### Acceptance Criteria

1. THE System SHALL authenticate all API endpoints (except /login, /register, /verify-register-otp, /forgot-password, and /verify-reset-otp) using JWT validation.
2. WHEN a JWT expires, THE System SHALL return a 401 Unauthorized response and redirect the client to the login page.
3. THE System SHALL store passwords as bcrypt hashes with a minimum cost factor of 12; THE System SHALL NOT store or transmit plaintext passwords.
4. THE System SHALL enforce HTTPS for all client-server communication in production deployments.
5. WHEN a Doctor accesses a Patient's records, THE System SHALL verify that the Doctor is either the submitting Doctor or an Admin before returning the data.

---

### Requirement 18: Parser and Serialiser for CBC Data Exchange

**User Story:** As a developer, I want a well-defined serialisation format for CBC data, so that OCR output, API payloads, and database records remain consistent across the system.

#### Acceptance Criteria

1. THE System SHALL define a canonical CBC JSON schema with fields: `rbc` (float), `mcv` (float), `mch` (float), `mchc` (float), `rdw` (float), `tlc` (float), `plt` (float), `hgb` (float).
2. WHEN a CBC JSON object is serialised and then deserialised, THE System SHALL produce an object equal to the original within floating-point precision of 6 decimal places (round-trip property).
3. THE System SHALL validate every incoming CBC JSON payload against the canonical schema before passing it to the Prediction_Engine.
4. IF a CBC JSON payload fails schema validation, THEN THE System SHALL return a 400 Bad Request response with a message listing each invalid field and the reason for rejection.

---

### Requirement 19: Doctor Module

**User Story:** As a Doctor, I want a dedicated workspace that shows only my patients' data and gives me the tools I need to manage their care, so that I can work efficiently without being exposed to other doctors' records or administrative functions.

#### Acceptance Criteria

1. WHEN a Doctor logs in, THE System SHALL redirect the Doctor to the Doctor Dashboard as the default landing page.
2. THE Doctor Dashboard SHALL display only the prediction records submitted under the authenticated Doctor's username; THE System SHALL NOT expose records belonging to other Doctors or Patients.
3. WHEN a Doctor submits a valid CBC input on behalf of a patient, THE Prediction_Engine SHALL record the submission under the Doctor's username and return the prediction result, Severity_Level, Anemia_Type, explanation, diet recommendations, and health tips.
4. WHEN a Doctor navigates to the Patient History section, THE System SHALL display all prediction records associated with that Doctor's account, ordered by date descending, paginated at 20 records per page.
5. WHEN a Doctor selects a specific patient record, THE System SHALL display the full result detail including CBC values, prediction, Severity_Level, Anemia_Type, explanation, diet recommendations, and health tips for that record.
6. WHEN a Doctor clicks "Download PDF" on any record in their patient list, THE Report_Generator SHALL produce a PDF report for that record within 5 seconds.
7. WHEN a patient result meets the Critical_Threshold, THE Alert_Service SHALL send the alert notification to the Doctor associated with that submission, as defined in Requirement 6.
8. IF a Doctor attempts to access a prediction record not associated with their username, THEN THE System SHALL return a 403 Forbidden response and log the access attempt.
9. IF a Doctor attempts to access any Admin-only endpoint (user management, system metrics, retraining pipeline, alert log), THEN THE System SHALL return a 403 Forbidden response.
10. THE System SHALL NOT allow a Doctor to create, deactivate, or modify other user accounts.
11. THE System SHALL NOT allow a Doctor to trigger model retraining.

---

### Requirement 20: Admin Module

**User Story:** As an Admin, I want a dedicated control panel that gives me full visibility over all system activity and user accounts, so that I can maintain the platform without being able to interfere with clinical prediction workflows.

#### Acceptance Criteria

1. WHEN an Admin logs in, THE System SHALL redirect the Admin to the Admin Dashboard as the default landing page, as defined in Requirement 15.
2. THE Admin Dashboard SHALL display all prediction records across all users; THE System SHALL NOT restrict the Admin's view to a subset of records.
3. WHEN an Admin navigates to the User Management section, THE System SHALL display a searchable, filterable list of all user accounts showing user_id, username, email, and role.
4. WHEN an Admin submits a valid create-user request with username, email, password, and role (patient, doctor, or admin), THE System SHALL create the account immediately without requiring OTP verification and return a 201 Created response.
5. WHEN an Admin deactivates a non-admin user account, THE System SHALL set the account status to "inactive", prevent that user from logging in, and return a 200 OK response; THE System SHALL NOT permanently delete the account or its associated prediction records.
6. WHEN an Admin navigates to the Alert Log section, THE System SHALL display all alert records with columns for recipient username, patient username, alert timestamp, HGB value, Severity_Level, and delivery status.
7. WHEN an Admin initiates model retraining by uploading a valid CSV file, THE Retraining_Pipeline SHALL process the request as defined in Requirement 16.
8. THE Admin Dashboard SHALL display the following system metrics: total registered users by role, total CBC predictions, total triage assessments, prediction counts by Severity_Level, prediction counts by Anemia_Type, and total critical alerts sent.
9. IF an Admin attempts to submit a CBC prediction as though acting as a patient or doctor, THEN THE System SHALL return a 403 Forbidden response.
10. THE System SHALL NOT allow an Admin to deactivate another Admin account without a second Admin's confirmation.
11. THE System SHALL log every Admin action (account creation, deactivation, retraining trigger, alert log access) with the Admin's username and a timestamp.

---

### Requirement 21: Role-Based Access Control (RBAC)

**User Story:** As a system operator, I want a clearly defined and consistently enforced permission model for all three roles, so that no user can access data or perform actions beyond their authorised scope.

#### Acceptance Criteria

1. THE System SHALL recognise exactly three roles: Patient, Doctor, and Admin; THE System SHALL reject any JWT or session token that carries an unrecognised role value.
2. THE System SHALL enforce the following permission matrix on every authenticated API request:

   | Action | Patient | Doctor | Admin |
   |---|---|---|---|
   | Submit CBC prediction | ✓ (own records only) | ✓ (own records only) | ✗ |
   | View own prediction history | ✓ | ✓ | ✗ |
   | View other users' prediction records | ✗ | ✗ | ✓ |
   | Download PDF report (own records) | ✓ | ✓ | ✗ |
   | Receive critical alerts | ✗ | ✓ | ✗ |
   | View alert log | ✗ | ✗ | ✓ |
   | Create user accounts | ✗ | ✗ | ✓ |
   | Deactivate user accounts | ✗ | ✗ | ✓ |
   | View all user accounts | ✗ | ✗ | ✓ |
   | View system metrics dashboard | ✗ | ✗ | ✓ |
   | Trigger model retraining | ✗ | ✗ | ✓ |
   | Update own profile (password, language) | ✓ | ✓ | ✓ |

3. WHEN a request arrives at a protected endpoint, THE System SHALL extract the role claim from the validated JWT and compare it against the required role for that endpoint before executing any business logic.
4. IF the role claim in the JWT does not satisfy the required role for the requested endpoint, THEN THE System SHALL return a 403 Forbidden response with a message stating "Insufficient permissions" and SHALL NOT execute the endpoint's business logic.
5. THE System SHALL map API endpoints to required roles as follows:
   - `POST /predict` — Patient or Doctor
   - `GET /reports` — Patient (own records), Doctor (own records), Admin (all records)
   - `GET /api/stats` — Admin only
   - `GET /api/users` — Admin only
   - `POST /api/users` — Admin only
   - `PATCH /api/users/{user_id}/deactivate` — Admin only
   - `GET /api/alerts` — Admin only
   - `POST /api/retrain` — Admin only
   - `GET /api/reports/{patient_id}` — Patient (own record), Doctor (own record), Admin (any record)
6. THE System SHALL validate the role claim on every request; THE System SHALL NOT cache role decisions across requests.
7. WHEN a Patient or Doctor requests `GET /reports`, THE System SHALL filter the result set to records where the `username` column matches the authenticated user's username; THE System SHALL NOT return records belonging to other users.
8. IF a user's account is deactivated, THEN THE System SHALL reject all subsequent authentication attempts for that account with a 401 Unauthorized response and a message stating "Account is inactive".
9. THE System SHALL record every 403 Forbidden response in an access-violation log, including the requesting username, the requested endpoint, the role claim presented, and the timestamp.
