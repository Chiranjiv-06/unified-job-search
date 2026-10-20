# System Requirements Specification (SRS)

## 1. Functional Requirements (FR)

- **FR-1 Authentication**: Candidates can register with email and password, log in, retrieve JWT tokens, and log out.
- **FR-2 Candidate Profile**: Candidates can maintain their personal profile, skills, education, preferred roles, locations, experience level, and work mode.
- **FR-3 Resume Management**: Support PDF uploads, extract text using `pypdf`, identify extracted skills/experience, and provide resume improvement tips.
- **FR-4 Job Discovery & Manual Import**: Add jobs manually, import from permitted URLs or feeds, storing metadata (skills, experience, salary, company).
- **FR-5 Rule-Based Suitability Matching**: Explainable match scoring comparing required/preferred skills, education, experience, and location constraints without paid AI APIs.
- **FR-6 Verification & Risk Signals**: Analyze official domain matches, recruiter corroboration, conflicting details, and potential fraud flags with clear evidence URLs.
- **FR-7 Application Tracking**: Manage job applications across statuses (`SAVED`, `READY_TO_APPLY`, `APPLIED`, `INTERVIEW`, `OFFER`, `REJECTED`, etc.) and prevent duplicate applications.
- **FR-8 Reminders & Follow-Ups**: Candidate-configured response period (e.g., 2 days) triggering follow-up reminders when no response is received.
- **FR-9 Email Sync & Classification**: Connect email accounts with authorization, classify recruitment messages, and correlate with applications.
- **FR-10 Real-Time Dashboard**: Display actionable job metrics, upcoming reminders, recent application status changes, and recommendations.

## 2. Non-Functional Requirements (NFR)

- **NFR-1 Security**: Bcrypt password hashing, JWT stateless authentication, authorization checks on all user entities.
- **NFR-2 Performance**: API responses < 200ms for core CRUD operations.
- **NFR-3 Usability**: Responsive, intuitive dashboard suitable for undergraduate portfolio and technical interviews.
- **NFR-4 Maintainability**: Modular file structure separating database models, Pydantic schemas, service logic, and route handlers.
