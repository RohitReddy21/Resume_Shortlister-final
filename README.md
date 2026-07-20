# ResumeParser.AI authentication system

This workspace contains a production-ready authentication foundation for ResumeParser.AI using Next.js 15, React 19, Tailwind, FastAPI, and PostgreSQL.

## What is included

- Login
- Signup
- Forgot password
- Reset password
- Google OAuth entry point
- JWT access tokens
- Refresh token storage and rotation
- Role-based access control for Admin, Recruiter, Hiring Manager, and Candidate

## Quick start

For a full feature-by-feature explanation of the current app, see [docs/functionality-overview.md](docs/functionality-overview.md).

For the exact Windows commands that worked on this machine, including the `uvicorn` fix and background start commands, see [docs/run-local.md](docs/run-local.md).

For hosting the full application on Render with Docker, see [docs/deploy-render.md](docs/deploy-render.md).

1. Start PostgreSQL (optional with Docker):
   ```powershell
   docker compose up -d
   ```

   If Docker Desktop cannot run on your machine (virtualization disabled), skip this step and use the SQLite fallback or a hosted Postgres.

2. Local dev (SQLite fallback, no Docker required):
   ```powershell
   cd backend
   pip install -r requirements.txt
   # Create SQLite file and run migrations (the app will create tables automatically)
   uvicorn app.main:app --reload --port 8000
   ```

3. Use a hosted/Postgres DB instead of Docker (example using environment variable):
   - Create a database on Supabase / Railway / ElephantSQL and take the connection string.
   - Create a `.env` in `backend` and set:
     ```text
     DATABASE_URL=postgresql+psycopg2://<user>:<password>@<host>:<port>/<db>
     SECRET_KEY=<your-secret>
     ```
   - Then run the API as above.

4. Frontend:
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

Seeding an admin user (local dev)

1. Open a terminal in `backend` and run:

```powershell
python -m pip install -r requirements.txt
python scripts/seed_admin.py --email admin@example.com --password YourSecurePassword
```

This creates an `Admin` role user in the local SQLite database (or your configured Postgres database).

## Security notes

- Replace the default secret key in backend/.env.
- Configure Google OAuth credentials before enabling the provider.
- In production, move password reset emails to a provider such as SendGrid, SES, or Resend.
