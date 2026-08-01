"""Pure unit tests for the persistence enums/models (no DB, no app)."""

from assistant.infrastructure.memory.models import ApprovalStatus, CCRunStatus


def test_cc_run_status_values() -> None:
    assert CCRunStatus.queued == "queued"
    assert CCRunStatus.running == "running"
    assert CCRunStatus.reviewing == "reviewing"
    assert CCRunStatus.succeeded == "succeeded"
    assert CCRunStatus.failed == "failed"
    assert CCRunStatus.aborted == "aborted"


def test_cc_run_status_members() -> None:
    values = {s.value for s in CCRunStatus}
    assert values == {"queued", "running", "reviewing", "succeeded", "failed", "aborted"}


def test_approval_status_values() -> None:
    assert ApprovalStatus.pending == "pending"
    assert ApprovalStatus.approved == "approved"
    assert ApprovalStatus.rejected == "rejected"


def test_approval_status_members() -> None:
    values = {s.value for s in ApprovalStatus}
    assert values == {"pending", "approved", "rejected"}
