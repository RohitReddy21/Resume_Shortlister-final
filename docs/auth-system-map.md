# ResumeParser.AI authentication system map

This project implements a production-ready authentication stack for ResumeParser.AI using Next.js 15, React 19, Tailwind, shadcn-style UI components, FastAPI, and PostgreSQL.

## File-by-file purpose

- docs/auth-system-map.md: explains the role of every file before implementation.
- docker-compose.yml: starts PostgreSQL locally for development.
- backend/requirements.txt: Python dependencies for FastAPI, authentication, and PostgreSQL integration.
- backend/.env.example: environment variables for the API service.
- backend/app/main.py: FastAPI entry point and app bootstrap.
- backend/app/core/config.py: environment-based configuration.
- backend/app/core/database.py: SQLAlchemy engine, sessions, and table bootstrap.
- backend/app/core/security.py: hashing, JWT generation, and password utilities.
- backend/app/models/user.py: user persistence model.
- backend/app/models/refresh_token.py: refresh token persistence model.
- backend/app/schemas/auth.py: request and response validation models for auth.
- backend/app/crud/user.py: database operations for users and tokens.
- backend/app/api/deps.py: shared FastAPI dependencies for auth and database access.
- backend/app/api/routers/auth.py: login, signup, forgot/reset password, Google OAuth, refresh, and profile endpoints.
- backend/app/api/routers/admin.py: admin-only role-based management endpoints.
- backend/app/services/auth_service.py: business logic for token issuance and password reset flows.
- backend/app/services/email_service.py: placeholder email provider for password reset notifications.
- backend/app/db/schema.sql: relational schema for PostgreSQL.
- frontend/package.json: Next.js and frontend dependencies.
- frontend/tsconfig.json: TypeScript compiler configuration.
- frontend/next-env.d.ts: Next.js TypeScript shims.
- frontend/next.config.ts: app configuration.
- frontend/postcss.config.js: Tailwind PostCSS config.
- frontend/tailwind.config.ts: Tailwind theme and content scanning.
- frontend/.env.example: frontend environment variables.
- frontend/src/app/layout.tsx: root layout and global shell.
- frontend/src/app/globals.css: Tailwind base styles and theme variables.
- frontend/src/app/page.tsx: public landing page.
- frontend/src/app/login/page.tsx: login experience.
- frontend/src/app/signup/page.tsx: signup experience.
- frontend/src/app/forgot-password/page.tsx: forgot password experience.
- frontend/src/app/reset-password/page.tsx: password reset experience.
- frontend/src/app/dashboard/page.tsx: protected dashboard for authenticated users.
- frontend/src/app/oauth/callback/page.tsx: handles Google OAuth result.
- frontend/src/components/auth/auth-shell.tsx: shared auth page layout.
- frontend/src/components/auth/auth-form.tsx: reusable authentication form UI.
- frontend/src/components/ui/button.tsx: button primitive.
- frontend/src/components/ui/card.tsx: card primitive.
- frontend/src/components/ui/input.tsx: input primitive.
- frontend/src/components/ui/label.tsx: label primitive.
- frontend/src/components/ui/alert.tsx: alert primitive.
- frontend/src/lib/api.ts: API client for backend communication.
- frontend/src/lib/auth.ts: token persistence helpers.
- frontend/src/middleware.ts: route protection using access tokens.
- frontend/src/types/auth.ts: frontend auth shared types.
