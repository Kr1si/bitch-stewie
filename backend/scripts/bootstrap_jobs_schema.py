"""Idempotently create the Procrastinate job tables.

Called by `make jobs-schema`. Safe to run on every boot: checks for the
procrastinate_jobs table first and only applies the schema if it's missing.
"""

from sqlalchemy import text

from assistant.application.services.jobs_service import job_app
from assistant.infrastructure.memory.sync_db import get_sync_session_factory


def main() -> None:
    with get_sync_session_factory()() as s:
        exists = s.execute(
            text("SELECT to_regclass('procrastinate_jobs')")
        ).scalar()
    if exists:
        print("Procrastinate schema already present")
        return
    with job_app.open():
        job_app.schema_manager.apply_schema()
    print("Procrastinate schema created")


if __name__ == "__main__":
    main()
