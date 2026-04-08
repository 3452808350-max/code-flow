# Harness Lab Summary

This repository now targets a research-first Harness Lab instead of the earlier workflow-centric app or the interim prototype.

## Primary architecture

- `backend/app/harness_lab/context`: layered context assembly
- `backend/app/harness_lab/constraints`: natural-language guardrails and verdicts
- `backend/app/harness_lab/boundary`: tool gateway and patch staging
- `backend/app/harness_lab/orchestrator`: task graph construction
- `backend/app/harness_lab/prompting`: structured prompt frames
- `backend/app/harness_lab/runtime`: session/run/replay lifecycle
- `backend/app/harness_lab/optimizer`: policy compare and experiments
- `frontend/src/lab`: Harness Lab workbench

## Primary user experience

- create a research session from a natural-language goal
- inspect context blocks, prompt frames, and task graph
- run the session under policy preflight
- approve or deny risky actions
- inspect replays, compare harness policies, and record experiments

## Repository status

The active repository surface is now the Harness Lab core and workbench.
