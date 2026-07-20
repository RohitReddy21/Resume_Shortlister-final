# ResumeParser.AI Functionality Overview

This document describes the functionality implemented so far, how the frontend and backend work together, and where the important files live.

## Current Stack

| Layer | Technology | Purpose |
| --- | --- | --- |
| Frontend | Next.js 15, React 19, Tailwind CSS | User interface, authentication pages, dashboard pages, ATS score display |
| Backend | FastAPI, SQLAlchemy, Pydantic | API endpoints, auth, jobs, resume parsing, anonymization, ATS scoring |
| Local DB | SQLite by default | Local development data storage in `backend/dev.db` |
| Optional DB | PostgreSQL | Supported through `DATABASE_URL` |
| Resume processing | Inline FastAPI service functions | Resume parsing and anonymization run in-process |

## High-Level Architecture

```text
Browser
  |
  | Next.js pages call frontend/src/lib/api.ts
  v
Frontend dev server: http://localhost:3000
  |
  | fetch http://localhost:8000/api/v1/...
  v
FastAPI backend: http://localhost:8000
  |
  | SQLAlchemy models
  v
SQLite dev DB: backend/dev.db
```

The backend enables CORS for `http://localhost:3000` in `backend/app/main.py`, so the browser can call the API during local development.

## Frontend Functionality

### Public Home Page

Path: `/`

File: `frontend/src/app/page.tsx`

What it does:

- Shows the ResumeParser.AI landing card.
- Provides links to sign in and create an account.

How it works:

- Uses Next.js `Link` components for navigation to `/login` and `/signup`.
- Does not require authentication.

### Login Page

Path: `/login`

File: `frontend/src/app/login/page.tsx`

What it does:

- Lets a user sign in with email and password.
- On success, redirects to `/dashboard`.
- Shows backend/API errors inline.

How it works:

1. User submits the login form.
2. The page calls `login()` from `frontend/src/lib/api.ts`.
3. `login()` sends `POST /api/v1/auth/login` to the backend.
4. Backend returns an access token and refresh token.
5. `saveTokens()` in `frontend/src/lib/auth.ts` stores tokens in:
   - `localStorage` under `resumeparser.tokens`
   - cookies named `access_token` and `refresh_token`
6. The page uses `router.push('/dashboard')`.

Why both localStorage and cookies are used:

- `localStorage` is used by client-side API calls to set the `Authorization` header.
- Cookies are read by Next middleware to protect dashboard routes.

### Signup Page

Path: `/signup`

File: `frontend/src/app/signup/page.tsx`

What it does:

- Lets a new user create an account.
- Supports role selection: Candidate, Recruiter, Hiring Manager, Admin.
- On success, saves tokens and redirects to `/dashboard`.

How it works:

1. User submits full name, email, password, and role.
2. Frontend calls `signup()` in `frontend/src/lib/api.ts`.
3. Backend creates the user and returns tokens.
4. Frontend stores tokens and redirects to the dashboard.

### Forgot Password Page

Path: `/forgot-password`

File: `frontend/src/app/forgot-password/page.tsx`

What it does:

- Lets a user request a password reset email.

How it works:

1. Frontend sends the email to `POST /api/v1/auth/forgot-password`.
2. Backend creates a reset token.
3. Backend calls the email service.
4. In local development, email sending depends on configured SMTP settings.

### Reset Password Page

Path: `/reset-password`

File: `frontend/src/app/reset-password/page.tsx`

What it does:

- Lets a user set a new password using a token in the URL.

How it works:

1. Page reads the reset token from the query string.
2. User enters a new password.
3. Frontend sends `POST /api/v1/auth/reset-password`.
4. Backend validates the token and updates the stored password hash.
5. User is redirected to `/login`.

### OAuth Callback Page

Path: `/oauth/callback`

File: `frontend/src/app/oauth/callback/page.tsx`

What it does:

- Receives OAuth tokens after Google auth callback.
- Saves tokens and redirects to `/dashboard`.

Current state:

- The backend has Google OAuth endpoint scaffolding.
- Google OAuth requires `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and related settings before it works in production.

## Dashboard Functionality

Dashboard pages are protected by middleware.

Middleware file: `frontend/src/middleware.ts`

How protection works:

1. Any route under `/dashboard` is protected.
2. Middleware checks for an `access_token` cookie.
3. If missing, the user is redirected to `/login`.
4. If present, the dashboard route is allowed to render.
5. The page still calls `/api/v1/auth/me` client-side to confirm the token is valid.

### Shared Dashboard Frame

Files:

- `frontend/src/components/dashboard/dashboard-frame.tsx`
- `frontend/src/components/dashboard/dashboard-shell.tsx`
- `frontend/src/components/dashboard/dashboard-sidebar.tsx`

What it does:

- Provides the shared dashboard layout.
- Shows sidebar navigation on desktop.
- Shows a mobile menu button and slide-out drawer on mobile.
- Shows shared header actions: dark mode button, notifications link, sign out button.
- Checks the current logged-in user by calling `/api/v1/auth/me`.

How sign out works:

1. User clicks Sign out.
2. Frontend calls `logout()` from `frontend/src/lib/api.ts`.
3. Backend revokes the refresh token if it exists.
4. Frontend clears localStorage and cookies.
5. User is redirected to `/login`.

### Dashboard Overview

Path: `/dashboard`

File: `frontend/src/app/dashboard/page.tsx`

What it shows:

- Summary stat cards.
- Recent candidates.
- Hiring pipeline summary.
- Recent jobs.
- Quick action links.
- ATS score panel.

Current data state:

- Most dashboard lists are static placeholder data for UI workflow.
- ATS score panel calls a real backend endpoint.

### Candidates Page

Path: `/dashboard/candidates`

Files:

- `frontend/src/app/dashboard/candidates/page.tsx`
- `frontend/src/components/dashboard/resume-upload-panel.tsx`

What it shows:

- Resume upload form.
- Optional existing candidate ID field.
- Recent upload status cards.
- Uploaded resume list from the backend.
- Resume IDs for ATS scoring.

Current data state:

- Uploads real resume files through `POST /api/v1/resumes/upload`.
- Lists resume records through `GET /api/v1/resumes`.
- Checks async task status when a task ID exists.
- Fetches parsed resume JSON through `GET /api/v1/resumes/parsed/{upload_id}`.
- Lets a recruiter select a job and create an application from an uploaded resume through `POST /api/v1/applications`.
- A full candidate directory API is still separate future work.

### Jobs Page

Path: `/dashboard/jobs`

Files:

- `frontend/src/app/dashboard/jobs/page.tsx`
- `frontend/src/components/dashboard/job-manager.tsx`

What it shows:

- Job creation form.
- Backend job list.
- Job IDs for ATS scoring.
- Delete action for local cleanup.

Current data state:

- Creates jobs through `POST /api/v1/jobs`.
- Lists jobs through `GET /api/v1/jobs`.
- Deletes jobs through `DELETE /api/v1/jobs/{job_id}`.
- Skills and locations are entered as comma-separated values in the frontend and sent as arrays.

### Pipeline Page

Path: `/dashboard/pipeline`

File: `frontend/src/app/dashboard/pipeline/page.tsx`

What it shows:

- A job selector.
- A horizontal Kanban board grouped by application stage.
- Candidate cards, stage drag/drop, activity timeline, and comments.

Current data state:

- Lists jobs through `GET /api/v1/jobs`.
- Loads application columns through `GET /api/v1/pipeline/{job_id}`.
- Moves candidates between stages through `PATCH /api/v1/applications/{app_id}/stage`.
- Adds comments and @mention notifications through the pipeline comments endpoints.

### Notifications Page

Path: `/dashboard/notifications`

File: `frontend/src/app/dashboard/notifications/page.tsx`

What it shows:

- Notifications card.
- Notification settings/explanation panel.

Current data state:

- Lists current-user notifications through `GET /api/v1/notifications`.
- Marks notifications read through `PATCH /api/v1/notifications/{notification_id}/read`.

## Frontend API Layer

File: `frontend/src/lib/api.ts`

Responsibilities:

- Defines `API_URL`, defaulting to `http://localhost:8000`.
- Wraps `fetch()` calls in a shared `request<T>()` helper.
- Adds `Content-Type: application/json`.
- Skips the JSON content type for `FormData` uploads so the browser can set the multipart boundary.
- Adds `Authorization: Bearer <access_token>` when a token exists in localStorage.
- Parses backend errors into readable messages.

Implemented frontend API functions:

| Function | Backend endpoint | Purpose |
| --- | --- | --- |
| `login()` | `POST /api/v1/auth/login` | Sign in and save tokens |
| `signup()` | `POST /api/v1/auth/signup` | Create account and save tokens |
| `forgotPassword()` | `POST /api/v1/auth/forgot-password` | Request reset email |
| `resetPassword()` | `POST /api/v1/auth/reset-password` | Update password using reset token |
| `me()` | `GET /api/v1/auth/me` | Load current user |
| `logout()` | `POST /api/v1/auth/logout` | Revoke refresh token and clear tokens |
| `getATSScore()` | `GET /api/v1/ats/score/{resume_id}/{job_id}` | Load ATS match score |
| `listJobs()` | `GET /api/v1/jobs` | Load jobs for the Jobs dashboard page |
| `createJob()` | `POST /api/v1/jobs` | Create a job from the frontend form |
| `deleteJob()` | `DELETE /api/v1/jobs/{job_id}` | Delete a job from the frontend list |
| `listResumes()` | `GET /api/v1/resumes` | Load uploaded resume records |
| `uploadResume()` | `POST /api/v1/resumes/upload` | Upload one resume file with multipart form data |
| `getResumeStatus()` | `GET /api/v1/resumes/status/{task_id}` | Legacy endpoint; inline deployments return 410 |
| `getParsedResume()` | `GET /api/v1/resumes/parsed/{upload_id}` | Load parsed resume JSON |
| `createApplication()` | `POST /api/v1/applications` | Attach a candidate/resume to a job pipeline |
| `listNotifications()` | `GET /api/v1/notifications` | Load current-user notifications |
| `markNotificationRead()` | `PATCH /api/v1/notifications/{notification_id}/read` | Mark one notification as read |

## Token Storage

File: `frontend/src/lib/auth.ts`

Stored values:

- `localStorage['resumeparser.tokens']`
- `access_token` cookie
- `refresh_token` cookie

Functions:

- `saveTokens(tokens)`: saves both localStorage and cookies.
- `getStoredTokens()`: reads tokens from localStorage.
- `getAccessToken()`: returns the access token for API calls.
- `clearTokens()`: removes localStorage and cookies.

## Backend App Setup

File: `backend/app/main.py`

What happens at startup:

1. Creates FastAPI app.
2. Enables CORS for the frontend URL.
3. Registers routers under `/api/v1`.
4. Calls `init_db()` to create missing tables.
5. Applies small compatibility migrations for older local SQLite databases, including `applications.pipeline_order`.
6. Exposes `/health`.

Registered routers:

| Router | Prefix | Purpose |
| --- | --- | --- |
| Auth | `/api/v1/auth` | Signup, login, reset, OAuth, current user |
| Admin | `/api/v1/admin` | Admin-only endpoints |
| Parser | `/api/v1/resumes/...` | Upload, parse status, parsed resume retrieval |
| Anonymize | `/api/v1/resumes/...` | Mask/anonymize resume outputs |
| Jobs | `/api/v1/jobs` | Job CRUD |
| ATS | `/api/v1/ats` | Resume-to-job scoring |

## Backend Authentication

Important files:

- `backend/app/api/routers/auth.py`
- `backend/app/services/auth_service.py`
- `backend/app/core/security.py`
- `backend/app/crud/user.py`
- `backend/app/api/deps.py`
- `backend/app/models/user.py`
- `backend/app/models/refresh_token.py`

### Signup

Endpoint: `POST /api/v1/auth/signup`

Payload:

```json
{
  "email": "user@example.com",
  "password": "Password123",
  "full_name": "User Name",
  "role": "Candidate"
}
```

How it works:

1. Validates the payload with Pydantic.
2. Checks if the email is already registered.
3. Hashes the password using Passlib bcrypt.
4. Creates a `User` row.
5. Issues JWT access and refresh tokens.
6. Stores the refresh token in `refresh_tokens`.
7. Returns tokens to the frontend.

### Login

Endpoint: `POST /api/v1/auth/login`

Payload:

```json
{
  "email": "user@example.com",
  "password": "Password123"
}
```

How it works:

1. Looks up the user by email.
2. Verifies the password hash.
3. Issues a new access token and refresh token.
4. Stores refresh token in the database.
5. Returns tokens.

### Current User

Endpoint: `GET /api/v1/auth/me`

How it works:

1. Frontend sends `Authorization: Bearer <access_token>`.
2. Backend decodes the JWT.
3. Backend loads the user by `sub`.
4. If valid and active, user profile is returned.

### Refresh Token

Endpoint: `POST /api/v1/auth/refresh`

How it works:

1. Backend checks the refresh token record.
2. Rejects revoked or expired tokens.
3. Decodes the JWT.
4. Revokes the old refresh token.
5. Issues a new access/refresh pair.

### Logout

Endpoint: `POST /api/v1/auth/logout`

How it works:

1. Frontend sends current refresh token.
2. Backend marks it revoked if found.
3. Frontend clears local tokens and cookies.

### Role Protection

File: `backend/app/api/deps.py`

Important functions:

- `get_current_user()`: validates bearer token and loads current user.
- `require_role(...)`: restricts endpoints by role.

Example:

- `GET /api/v1/admin/users` requires role `Admin`.

## Jobs Functionality

Files:

- `backend/app/api/routers/jobs.py`
- `backend/app/schemas/jobs.py`
- `backend/app/models/ats/job.py`

Endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/jobs` | Create job |
| `GET` | `/api/v1/jobs` | List jobs, optionally by status |
| `GET` | `/api/v1/jobs/{job_id}` | Get one job |
| `PUT` | `/api/v1/jobs/{job_id}` | Update job |
| `DELETE` | `/api/v1/jobs/{job_id}` | Delete job |

Job fields:

- `title`
- `description`
- `department_id`
- `hiring_manager_id`
- `skills`
- `locations`
- `remote_type`: `onsite`, `remote`, `hybrid`
- `status`: `draft`, `published`, `closed`
- `min_salary`
- `max_salary`
- `currency`

How it works:

- Skills and locations are stored as JSON text in the database.
- `JobOut` converts stored JSON text back into arrays for frontend responses.
- `JobCreate` and `JobUpdate` validate payloads.
- Salary bounds are validated so min salary cannot exceed max salary.

Frontend workflow:

1. User opens `Dashboard -> Jobs`.
2. `JobManager` loads jobs with `listJobs()`.
3. User fills title, locations, description, skills, remote type, status, and optional salary fields.
4. Skills and locations are split by comma and sent as arrays.
5. Backend creates the job and returns the generated job ID.
6. The job ID can be used on the ATS score panel.

## Resume Parser Functionality

Files:

- `backend/app/api/routers/parser.py`
- `backend/app/services/parser/tasks.py`
- `backend/app/services/parser/orchestrator.py`
- `backend/app/services/parser/extractor.py`
- `backend/app/services/parser/nlp.py`
- `backend/app/services/parser/ocr.py`
- `backend/app/services/parser/openai_fallback.py`
- `backend/app/services/parser/schema.py`

### Upload Resume

Endpoint: `POST /api/v1/resumes/upload`

Input:

- `file`: uploaded resume file
- `candidate_id`: optional form value

How it works:

1. Validates filename.
2. Saves the uploaded file under `backend/uploads/resumes`.
3. Rejects files larger than 20 MB.
4. Uses the provided candidate, or creates a placeholder candidate.
5. Creates a `Resume` row.
6. Parses inline during the upload request.
7. Returns upload ID, resume ID, file name, saved path, parse mode, and status.

Parse modes:

- `inline`: parsed during the upload request. This is the default local mode.
- `not_parsed`: file was saved, but parsing failed.

### List Uploaded Resumes

Endpoint: `GET /api/v1/resumes`

How it works:

- Returns the latest uploaded resume records.
- Includes resume ID, candidate ID, candidate name/email when available, upload title, current version ID, status, and created time.
- Status is `parsed` when the resume has a current parsed version; otherwise it is `processing`.
- The frontend Candidates page uses this endpoint for the uploaded resume list.

### Check Parse Status

Endpoint: `GET /api/v1/resumes/status/{task_id}`

How it works:

- Inline deployments do not create background task IDs.
- Returns `410 Gone` with a message explaining that parsing happens inline.

### Get Parsed Resume

Endpoint: `GET /api/v1/resumes/parsed/{upload_id}`

How it works:

1. Finds the resume by upload ID.
2. If parsing is not complete, returns `{"status": "processing"}`.
3. If a current version exists, reads `parsed_json`.
4. Returns parsed resume JSON.

### Parser Service Flow

The parser orchestrator extracts text and structured sections.

Expected parsed fields include:

- full name
- emails
- phones
- skills
- experiences
- education
- certifications
- languages
- projects
- parsed text

Notes:

- Some parser dependencies are heavy and optional.
- Resume upload parsing does not require Redis or background workers.

## ATS Scoring Functionality

Files:

- `backend/app/api/routers/ats.py`
- `backend/app/services/ats/scoring.py`
- `backend/app/schemas/ats.py`
- `frontend/src/components/dashboard/ats-score-panel.tsx`

### Score Resume Against Job

Endpoint: `GET /api/v1/ats/score/{resume_id}/{job_id}`

What it does:

- Scores a parsed resume against a job.
- Returns total score, component scores, matched/missing skills, strengths, weaknesses, recommendations, and explanation.

How it works:

1. Loads the `Resume`.
2. Confirms the resume has a current parsed version.
3. Loads `ResumeVersion.parsed_json`.
4. Loads the `Job`.
5. Calls `score_resume_against_job(parsed_resume, job)`.
6. Returns `ATSScoreResponse`.

Scoring components:

| Component | Meaning |
| --- | --- |
| `skills` | Required job skills matched by parsed resume skills |
| `experience` | Semantic or fallback overlap between work history and job description |
| `similarity` | Overall contextual similarity between full resume text and job description |
| `projects` | Project relevance to job description |
| `achievements` | Heuristic score for metrics, numbers, impact verbs |
| `education` | Whether education/certifications/languages were detected |
| `culture_fit` | Soft skill/culture keyword overlap |

Confidence score:

- Based on parsed resume completeness.
- Counts extracted standard sections like skills, experiences, education, projects, emails, and phones.

Semantic scoring:

- Disabled by default for local reliability.
- If `ATS_ENABLE_SEMANTIC_SCORING=true` and a local `all-MiniLM-L6-v2` model is available, it uses `sentence-transformers`.
- Otherwise it falls back to simpler text similarity without downloading model files.

Frontend ATS panel:

- Located on `/dashboard`.
- User enters a parsed resume ID and job ID.
- Frontend calls `getATSScore()`.
- UI shows:
  - overall match score
  - component scores and weights
  - matched skills
  - missing skills
  - strengths
  - weaknesses
  - recommendations

Current limitation:

- The frontend type/display currently focuses on the main visible fields.
- Backend also returns `confidence_score` and `score_breakdown`, which can be displayed in a future UI update.

## Resume Anonymization Functionality

Files:

- `backend/app/api/routers/anonymize.py`
- `backend/app/services/anonymizer.py`
- `backend/app/services/anonymizer_tasks.py`
- `backend/app/schemas/anonymize.py`

### Mask Resume

Endpoint: `POST /api/v1/resumes/{resume_id}/mask`

What it does:

- Runs anonymization inline for the requested resume.
- Supports text redaction/pseudonymization and image masking.

Mask policy fields:

- `pseudonymize`
- `image_blur`
- `image_blur_radius`
- `image_remove`
- `generate_pdf`
- `generate_docx`

How it works:

1. Checks the resume exists.
2. Validates mask policy.
3. Runs `anonymize_resume_task` directly.
4. Returns resume ID and completion status.

### Get Masked Metadata

Endpoint: `GET /api/v1/resumes/masked/{resume_id}`

How it works:

1. Checks the resume exists.
2. Prefers masked metadata stored on the current resume version.
3. Falls back to checking files under `uploads/resumes`.
4. Returns masked candidate ID, masked output paths, policy, and timestamp.

### Anonymizer Service

`backend/app/services/anonymizer.py` handles:

- deterministic masked candidate ID generation using HMAC
- PDF text redaction
- DOCX text replacement
- PDF image masking/blurring
- DOCX image masking/blurring

## Admin Functionality

File: `backend/app/api/routers/admin.py`

Endpoint:

| Method | Path | Required role | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/v1/admin/users` | `Admin` | Placeholder admin user management endpoint |

How it works:

- Uses `require_role("Admin")`.
- Validates JWT bearer token.
- Returns a message if the user is an Admin.

## Data Models

Main auth models:

- `User`
- `RefreshToken`

ATS/domain models:

- `Candidate`
- `Resume`
- `ResumeVersion`
- `Job`
- `Application`
- `Interview`
- `Skill`
- `JobSkill`
- `CandidateSkill`
- `Company`
- `Department`
- `HiringManager`
- `Role`
- `Permission`
- `RolePermission`
- `UserCompany`
- `Notification`
- `ActivityLog`
- `AuditLog`
- `Session`
- `Experience`
- `Education`
- `Certification`

Local development database:

- Default URL: `sqlite:///./dev.db`
- File location when running from backend directory: `backend/dev.db`

Production database:

- Set `DATABASE_URL` in `backend/.env`.
- Example: `postgresql+psycopg2://user:password@host:port/db`

## Local Run and Troubleshooting

Primary run guide:

- `docs/run-local.md`

Important local commands:

Start backend:

```powershell
cd C:\Users\PC\Desktop\resumeparsor\backend
C:\Users\PC\anaconda3\python.exe -m uvicorn app.main:app --reload --port 8000
```

Start frontend:

```powershell
cd C:\Users\PC\Desktop\resumeparsor\frontend
npm.cmd run dev
```

Fix stale Next cache:

```powershell
cd C:\Users\PC\Desktop\resumeparsor
powershell.exe -ExecutionPolicy Bypass -File .\scripts\restart-frontend.ps1
```

Common issue notes:

- `No module named uvicorn`: run backend with the Anaconda Python command above.
- `Cannot find module './825.js'`: stale `.next` cache or stale process on port 3000. Use `scripts/restart-frontend.ps1`.
- Login shows CORS and 500: backend crashed during request; fix backend error and restart backend.

## Current Implementation Status

Implemented and working:

- Public home page
- Login
- Signup
- Forgot password endpoint/UI
- Reset password endpoint/UI
- JWT access tokens
- Refresh token storage/revocation
- Dashboard route protection
- Dashboard desktop sidebar navigation
- Dashboard mobile menu/drawer
- Dashboard overview page
- Dashboard candidates/jobs/pipeline/notifications pages
- Dashboard Jobs page connected to backend job create/list/delete
- Dashboard Candidates page connected to resume upload/list/parse preview
- Backend job CRUD
- Resume upload endpoint
- Resume list endpoint
- Parse status endpoint
- Parsed resume endpoint
- ATS scoring endpoint
- Frontend ATS scoring panel
- Resume anonymization endpoints and task service
- Admin role-protected placeholder endpoint
- Local run/troubleshooting documentation
- Frontend restart script for stale Next cache

Partially implemented or next candidates:

- Add a full candidate directory API and candidate profile pages.
- Display backend `confidence_score` and `score_breakdown` in the ATS score UI.
- Add batch ATS scoring endpoint.
- Add full Alembic migrations instead of startup compatibility patches.
- Add production-grade email provider setup.
- Complete Google OAuth configuration.

## Important Files Map

| Area | Files |
| --- | --- |
| App startup | `backend/app/main.py` |
| Backend config | `backend/app/core/config.py` |
| Database setup | `backend/app/core/database.py` |
| Auth API | `backend/app/api/routers/auth.py` |
| Auth service | `backend/app/services/auth_service.py` |
| JWT/password logic | `backend/app/core/security.py` |
| Current user/roles | `backend/app/api/deps.py` |
| Jobs API | `backend/app/api/routers/jobs.py` |
| Parser API | `backend/app/api/routers/parser.py` |
| ATS API | `backend/app/api/routers/ats.py` |
| ATS scoring | `backend/app/services/ats/scoring.py` |
| Anonymize API | `backend/app/api/routers/anonymize.py` |
| Anonymizer service | `backend/app/services/anonymizer.py`, `backend/app/services/anonymizer_tasks.py` |
| Frontend API client | `frontend/src/lib/api.ts` |
| Frontend token storage | `frontend/src/lib/auth.ts` |
| Middleware | `frontend/src/middleware.ts` |
| Dashboard frame | `frontend/src/components/dashboard/dashboard-frame.tsx` |
| Dashboard shell/mobile menu | `frontend/src/components/dashboard/dashboard-shell.tsx` |
| Dashboard sidebar | `frontend/src/components/dashboard/dashboard-sidebar.tsx` |
| ATS score panel | `frontend/src/components/dashboard/ats-score-panel.tsx` |
| Job manager UI | `frontend/src/components/dashboard/job-manager.tsx` |
| Resume upload UI | `frontend/src/components/dashboard/resume-upload-panel.tsx` |
| Run guide | `docs/run-local.md` |
| Restart frontend script | `scripts/restart-frontend.ps1` |
