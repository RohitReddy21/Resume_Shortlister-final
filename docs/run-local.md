# Run Locally on Windows

These commands are written for PowerShell from this repository:

```powershell
cd C:\Users\PC\Desktop\resumeparsor
```

## What Is Running Now

- Backend API: http://localhost:8000
- Backend docs: http://localhost:8000/docs
- Frontend: http://localhost:3000

## Start the Backend

Use `python -m uvicorn` instead of running `uvicorn` directly. On this PC, the working Python is the Anaconda interpreter:

```powershell
cd C:\Users\PC\Desktop\resumeparsor\backend
C:\Users\PC\anaconda3\python.exe -m uvicorn app.main:app --reload --port 8000
```

Then verify it:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok"
}
```

## Start the Frontend

Use `npm.cmd` on this Windows setup because PowerShell may block the `npm.ps1` shim.

```powershell
cd C:\Users\PC\Desktop\resumeparsor\frontend
npm.cmd install
npm.cmd run dev
```

Open:

```text
http://localhost:3000
```

## Add Jobs and Upload Resumes from the Frontend

After the backend and frontend are running:

1. Open `http://localhost:3000`.
2. Sign up or log in.
3. Go to `Dashboard -> Jobs` to create jobs. The page saves jobs through `POST /api/v1/jobs` and lists them from `GET /api/v1/jobs`.
4. Go to `Dashboard -> Candidates` to upload resumes. The page uploads files through `POST /api/v1/resumes/upload`, lists uploaded resumes from `GET /api/v1/resumes`, and can check parsed results.
5. Use the shown resume ID and job ID on the Dashboard ATS score panel.

## Common Issue: No Module Named uvicorn

This happens when the Python interpreter you are using does not have the backend dependencies installed.

Use this exact command:

```powershell
C:\Users\PC\anaconda3\python.exe -m uvicorn app.main:app --reload --port 8000
```

Do not run:

```powershell
uvicorn app.main:app --reload --port 8000
```

If you want to use the project `.venv` instead, install dependencies into that same interpreter first:

```powershell
cd C:\Users\PC\Desktop\resumeparsor
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

The current `.venv` uses Python 3.14, so some pinned backend packages may fail to install. Anaconda Python is the known working option on this machine.

## Common Issue: Cannot Find Module './825.js'

This is a stale or corrupted Next.js build cache. Stop the frontend server, clear only the generated `.next` folder, and restart the frontend.

Fast fix:

```powershell
cd C:\Users\PC\Desktop\resumeparsor
powershell.exe -ExecutionPolicy Bypass -File .\scripts\restart-frontend.ps1
```

If `next dev` says `Port 3000 is in use, using available port 3002 instead`, the browser is probably still hitting a stale process on port 3000. Use the same fast fix above.

Find the frontend process:

```powershell
netstat -ano | findstr ":3000"
```

Stop the PID shown in the last column:

```powershell
Stop-Process -Id <PID>
```

Clear the generated cache:

```powershell
cd C:\Users\PC\Desktop\resumeparsor
Remove-Item -LiteralPath .\frontend\.next -Recurse -Force
```

Restart the frontend:

```powershell
cd C:\Users\PC\Desktop\resumeparsor\frontend
npm.cmd run dev
```

## Common Issue: Login Shows CORS and 500

If the browser says login was blocked by CORS and the console also shows `500 (Internal Server Error)`, the backend crashed while handling the request. Fix the backend error first; the missing CORS header is a symptom of the 500 response.

After source changes, restart the backend so it loads the current code:

```powershell
netstat -ano | findstr ":8000"
Stop-Process -Id <PID>

Start-Process -FilePath "cmd.exe" `
  -ArgumentList @("/k","cd /d C:\Users\PC\Desktop\resumeparsor\backend && C:\Users\PC\anaconda3\python.exe -m uvicorn app.main:app --reload --port 8000") `
  -WindowStyle Minimized
```

Verify CORS and login from PowerShell:

```powershell
$body = @{ email = "you@example.com"; password = "Password123" } | ConvertTo-Json
Invoke-WebRequest -Uri http://localhost:8000/api/v1/auth/login `
  -Method Post `
  -ContentType "application/json" `
  -Headers @{ Origin = "http://localhost:3000" } `
  -Body $body
```

## Start Both in the Background

From the repository root:

```powershell
cd C:\Users\PC\Desktop\resumeparsor
New-Item -ItemType Directory -Force -Path .run-logs | Out-Null

Start-Process -FilePath "C:\Users\PC\anaconda3\python.exe" `
  -ArgumentList @("-m","uvicorn","app.main:app","--reload","--port","8000") `
  -WorkingDirectory "C:\Users\PC\Desktop\resumeparsor\backend" `
  -RedirectStandardOutput ".run-logs\backend.out.log" `
  -RedirectStandardError ".run-logs\backend.err.log" `
  -WindowStyle Hidden

Start-Process -FilePath "npm.cmd" `
  -ArgumentList @("run","dev") `
  -WorkingDirectory "C:\Users\PC\Desktop\resumeparsor\frontend" `
  -RedirectStandardOutput ".run-logs\frontend.out.log" `
  -RedirectStandardError ".run-logs\frontend.err.log" `
  -WindowStyle Hidden
```

If the hidden frontend process exits immediately, start it in a minimized Command Prompt instead:

```powershell
Start-Process -FilePath "cmd.exe" `
  -ArgumentList @("/k","cd /d C:\Users\PC\Desktop\resumeparsor\frontend && npm.cmd run dev") `
  -WindowStyle Minimized
```

Check logs:

```powershell
Get-Content .run-logs\backend.err.log -Tail 80
Get-Content .run-logs\frontend.err.log -Tail 80
```

## Stop the App

Find processes listening on the app ports:

```powershell
netstat -ano | findstr ":8000"
netstat -ano | findstr ":3000"
```

Stop a process by PID:

```powershell
Stop-Process -Id <PID>
```

## Optional: Seed an Admin User

Run this once if you want a known admin login:

```powershell
cd C:\Users\PC\Desktop\resumeparsor\backend
C:\Users\PC\anaconda3\python.exe scripts\seed_admin.py --email admin@example.com --password YourSecurePassword
```

## Resume Parsing Notes

Auth, dashboard, jobs, and ATS score display can run with the backend and frontend only.

Resume upload parsing works locally without Redis or background workers. `POST /api/v1/resumes/upload` saves the file and parses it inline, so the frontend upload flow works with only the FastAPI backend running.
