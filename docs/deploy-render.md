# Deploy ResumeParser.AI backend on Render

This setup deploys only the FastAPI backend on Render. Deploy the Next.js frontend separately on Vercel with `frontend` as the project root.

- `resumeparser-api`: FastAPI backend
- `resumeparser-db`: managed Postgres database

The repository includes `render.yaml` and `backend/Dockerfile` so Render can create the backend stack from a GitHub repo.

## 1. Push the repo

Commit the current code and push it to GitHub. Do not commit local `.env` files, `backend/dev.db`, or uploaded resumes.

## 2. Create the Render Blueprint

In Render, create a new Blueprint from the GitHub repository. Render will read `render.yaml`.

When prompted for environment variables, set:

```text
ADMIN_PASSWORD=<your secure admin password>
```

`SECRET_KEY` is generated automatically. `DATABASE_URL` is wired from the managed Postgres database.

After Vercel gives you the frontend URL, set these on the Render backend service and redeploy:

```text
FRONTEND_URL=https://your-vercel-app.vercel.app
FRONTEND_HOSTNAME=your-vercel-app.vercel.app
```

## 3. Check deploy order

After the first deploy:

1. Open the backend service and confirm `/health` returns `{"status":"ok"}`.
2. Open the Vercel frontend.
3. Log in with:

```text
Email: admin@example.com
Password: the ADMIN_PASSWORD you entered
```

## 4. File uploads

Uploaded resumes are stored under `/data/uploads` on the backend service. The `render.yaml` backend service includes a persistent disk mounted at `/data`.

## 5. Optional production settings

Set these only when needed:

```text
OPENAI_API_KEY=<optional, for AI fallback parsing>
SMTP_HOST=<mail provider host>
SMTP_USERNAME=<mail provider username>
SMTP_PASSWORD=<mail provider password>
SMTP_FROM=no-reply@your-domain.com
GOOGLE_CLIENT_ID=<optional>
GOOGLE_CLIENT_SECRET=<optional>
GOOGLE_REDIRECT_URI=https://<backend-host>/api/v1/auth/google/callback
FRONTEND_URL=https://<custom-frontend-domain>
```

If you use a custom frontend domain, set `FRONTEND_URL` on the backend service to that full URL and `FRONTEND_HOSTNAME` to the bare hostname so CORS allows it.

## Local production smoke test

From the repo root:

```powershell
docker build -f backend/Dockerfile -t resumeparser-api .
```

Run the backend with a Postgres `DATABASE_URL` and then build/run the frontend with either:

```text
NEXT_PUBLIC_API_URL=https://your-backend-host
```

or:

```text
NEXT_PUBLIC_API_HOSTNAME=your-backend-host
```
