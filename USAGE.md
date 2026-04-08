# Harness Lab Usage

## Start the platform

### Backend
```bash
python3 -m uvicorn backend.app.main:app --reload --port 4600
```

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
