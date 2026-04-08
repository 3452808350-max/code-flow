#!/usr/bin/env python3
"""Print the current local development commands for Harness Lab."""


def main() -> None:
    print("Harness Lab development commands")
    print("1. Backend : python3 -m uvicorn backend.app.main:app --reload --port 4600")
    print("2. Frontend: cd frontend && npm install && npm run dev")
    print("3. Docs    : http://localhost:4600/docs")


if __name__ == "__main__":
    main()
