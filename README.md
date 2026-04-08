# Harness Lab

本仓库当前是一个`研究优先、断代重构、可回放 trace 导向`的 Harness 平台，而不是传统工作流产品或生产级 agent 服务。

## What It Is

- `backend/app/harness_lab/context`: 分层 context 管理
- `backend/app/harness_lab/constraints`: 自然语言约束与 policy verdict
- `backend/app/harness_lab/boundary`: 工具边界与 preflight
- `backend/app/harness_lab/orchestrator`: intent / task graph
- `backend/app/harness_lab/prompting`: structured prompt frame
- `backend/app/harness_lab/runtime`: session / run / replay runtime
- `backend/app/harness_lab/optimizer`: harness compare 与 experiment registry
- `frontend/src/lab`: Harness Lab 研究工作台

## Core Capabilities

- session-first research workflow
- layered context blocks with token-budget trimming
- natural-language constraints with deny-before-allow verdicts
- fixed prompt frame ordering
- replayable execution traces and approval chain
- harness policy comparison and experiment logging

## Main API Surface

- `POST /api/sessions`
- `POST /api/intent/declare`
- `POST /api/context/assemble`
- `POST /api/prompts/render`
- `POST /api/constraints/verify`
- `POST /api/runs`
- `GET /api/replays/{id}`
- `POST /api/policies/compare`
- `POST /api/experiments`

## Local Development

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

## Current Limits

- single-user local mode only
- no container sandbox yet
- model registry is heuristic in this build
- custom natural-language constraints are not deeply parsed yet
- DAG execution is schema-first but still single-worker at runtime
