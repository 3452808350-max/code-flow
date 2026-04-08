from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.app.harness_lab.control_plane.approvals import router as approvals_router
from backend.app.harness_lab.control_plane.candidates import router as candidates_router
from backend.app.harness_lab.control_plane.constraints import router as constraints_router
from backend.app.harness_lab.control_plane.context import router as context_router
from backend.app.harness_lab.control_plane.experiments import router as experiments_router
from backend.app.harness_lab.control_plane.evals import router as evals_router
from backend.app.harness_lab.control_plane.failure_clusters import router as failure_clusters_router
from backend.app.harness_lab.control_plane.intent import router as intent_router
from backend.app.harness_lab.control_plane.policies import router as policies_router
from backend.app.harness_lab.control_plane.prompts import router as prompts_router
from backend.app.harness_lab.control_plane.replays import router as replays_router
from backend.app.harness_lab.control_plane.runs import router as runs_router
from backend.app.harness_lab.control_plane.sessions import router as sessions_router
from backend.app.harness_lab.control_plane.system import router as system_router
from backend.app.harness_lab.control_plane.workers import router as workers_router
from backend.app.harness_lab.control_plane.workflows import router as workflows_router


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


app = FastAPI(
    title="Harness Lab",
    version="3.0.0",
    description="Research-first Harness Lab with layered context, natural-language constraints, prompt frames, policy verdicts, and replayable execution traces.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions_router)
app.include_router(intent_router)
app.include_router(context_router)
app.include_router(prompts_router)
app.include_router(constraints_router)
app.include_router(approvals_router)
app.include_router(runs_router)
app.include_router(replays_router)
app.include_router(policies_router)
app.include_router(experiments_router)
app.include_router(candidates_router)
app.include_router(evals_router)
app.include_router(workflows_router)
app.include_router(failure_clusters_router)
app.include_router(workers_router)
app.include_router(system_router)


@app.get("/")
async def root():
    return {
        "success": True,
        "data": {
            "name": "Harness Lab",
            "mode": "research_platform",
            "docs": "/docs",
        },
    }


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=4600)


if __name__ == "__main__":
    main()
