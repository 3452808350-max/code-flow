# Legacy Archive

This directory stores retired workflow-era code and scripts for historical reference only.

## Rules

- Treat all files under `legacy/` as read-only historical artifacts.
- Do not import or execute legacy code from active Harness Lab runtime paths.
- New features and fixes must be implemented in active platform modules, not in `legacy/`.

## Migration Map

| Original Path | Archived Path |
| --- | --- |
| `backend/app/core/__init__.py` | `legacy/code/backend_app_core/__init__.py` |
| `backend/app/core/intent_analyzer.py` | `legacy/code/backend_app_core/intent_analyzer.py` |
| `backend/app/core/preference_model.py` | `legacy/code/backend_app_core/preference_model.py` |
| `backend/app/core/reasoning_model.py` | `legacy/code/backend_app_core/reasoning_model.py` |
| `backend/app/core/task_planner.py` | `legacy/code/backend_app_core/task_planner.py` |
| `backend/app/core/vector_db.py` | `legacy/code/backend_app_core/vector_db.py` |
| `backend/app/core/workflow_engine.py` | `legacy/code/backend_app_core/workflow_engine.py` |
| `n8n/workflows/ai_workflow_template.json` | `legacy/code/workflow_era_scripts/ai_workflow_template.json` |
| `push_to_github.bat` | `legacy/code/workflow_era_scripts/push_to_github.bat` |
| `quick_start.py` | `legacy/code/workflow_era_scripts/quick_start.py` |
| `setup_github.md` | `legacy/code/workflow_era_scripts/setup_github.md` |
| `start_simple.py` | `legacy/code/workflow_era_scripts/start_simple.py` |
| `test_basic.py` | `legacy/code/workflow_era_scripts/test_basic.py` |
| `test_workflow.py` | `legacy/code/workflow_era_scripts/test_workflow.py` |

## Historical Context

These artifacts represent pre-Harness-Lab architecture phases and are retained only to preserve project history.
