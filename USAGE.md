# Harness Lab Usage

## Start the platform

### Infrastructure (Postgres, Redis, MinIO)
```bash
docker compose -f docker/docker-compose.yml up -d
```

### Backend
```bash
# Copy environment config
cp .env.example .env

# Edit .env to configure artifact backend:
# - HARNESS_ARTIFACT_BACKEND=local (default, filesystem storage)
# - HARNESS_ARTIFACT_BACKEND=s3 (S3-compatible, e.g., MinIO)

python3 -m uvicorn backend.app.main:app --reload --port 4600
```

### Artifact Backend Configuration

**Local filesystem (default for development):**
```bash
HARNESS_ARTIFACT_BACKEND=local
HARNESS_ARTIFACT_ROOT=backend/data/harness_lab/artifacts
```

**S3-compatible (MinIO for production-like testing):**
```bash
HARNESS_ARTIFACT_BACKEND=s3
HARNESS_ARTIFACT_BUCKET=harness-lab-artifacts
HARNESS_ARTIFACT_PREFIX=harness-lab
HARNESS_AWS_ENDPOINT_URL=http://localhost:9000
HARNESS_AWS_ACCESS_KEY_ID=minioadmin
HARNESS_AWS_SECRET_ACCESS_KEY=minioadmin
```

**AWS S3 (production):**
```bash
HARNESS_ARTIFACT_BACKEND=s3
HARNESS_ARTIFACT_BUCKET=my-harness-bucket
HARNESS_ARTIFACT_PREFIX=artifacts
HARNESS_AWS_REGION=us-east-1
HARNESS_AWS_ACCESS_KEY_ID=your-access-key
HARNESS_AWS_SECRET_ACCESS_KEY=your-secret-key
# Leave endpoint empty for AWS
```

Check artifact backend status:
- `GET /api/health` - shows `artifact_backend`, `artifact_ready`, `artifact_last_error`
- `GET /api/settings/catalog` - shows full `artifact_store` status

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open:
- Workbench: `http://localhost:3000`
- API docs: `http://localhost:4600/docs`

## Main workflow

1. Open the `Sessions` view.
2. Enter a natural-language goal plus optional path hint or shell command.
3. Create a session and inspect its intent declaration, context blocks, and prompt frame.
4. Execute the session as a run.
5. Resolve approvals when the run pauses on high-risk work.
6. Inspect `Replays`, `Policies`, and `Experiments`.

## Core APIs

- `POST /api/sessions`
- `POST /api/intent/declare`
- `POST /api/context/assemble`
- `POST /api/prompts/render`
- `POST /api/constraints/verify`
- `POST /api/runs`
- `GET /api/replays/{id}`
- `POST /api/policies/compare`
- `POST /api/experiments`

## Current operating model

- single-user local mode
- layered context + prompt frame assembly
- approval gates for risky tool actions
- replayable execution traces and artifact indexing
- published harness policy as the active runtime baseline
