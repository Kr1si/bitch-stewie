"""Pure unit tests for the Goal domain model (no DB, no app).

Covers enum values, Goal construction + defaults, and that the seed payload
validates against the model. DB-backed behavior (seed idempotency, the
scheduler) is exercised on krisiserver where Postgres lives.
"""

from assistant.application.services.memory_service import (
    Goal,
    GoalKind,
    GoalStatus,
)
from assistant.interface.cli.main import SEED_GOALS


def test_goal_kind_values() -> None:
    assert GoalKind.research == "research"
    assert GoalKind.coding == "coding"
    assert GoalKind.testing == "testing"


def test_goal_kind_members() -> None:
    assert {k.value for k in GoalKind} == {"research", "coding", "testing"}


def test_goal_status_values() -> None:
    assert GoalStatus.active == "active"
    assert GoalStatus.paused == "paused"
    assert GoalStatus.completed == "completed"


def test_goal_status_members() -> None:
    assert {s.value for s in GoalStatus} == {"active", "paused", "completed"}


def test_goal_column_defaults_are_configured() -> None:
    """Enum/scalar column defaults match the intended seed behavior.

    Note: like the existing CCRun model, these defaults apply at DB insert, not
    Python ``__init__`` — so we assert the column default args, not init values.
    """
    assert Goal.__table__.c.kind.default.arg == "research"
    assert Goal.__table__.c.status.default.arg == "active"
    assert Goal.__table__.c.cadence.default.arg == "0 7 * * *"


def test_goal_accepts_kind_coding_and_testing() -> None:
    assert Goal(title="c", kind=GoalKind.coding).kind == GoalKind.coding
    assert Goal(title="t", kind=GoalKind.testing).kind == GoalKind.testing


def test_seed_goals_validate_against_model() -> None:
    """Every SEED_GOALS payload must construct a Goal without error."""
    assert len(SEED_GOALS) >= 1
    for payload in SEED_GOALS:
        goal = Goal(**payload)
        assert goal.title
        # kind/status come from the payload (research/active); cron is 5 fields
        assert goal.kind == GoalKind(payload["kind"])
        # native_enum=False stores the raw string; GoalStatus(...) round-trips it
        assert GoalStatus(goal.status if goal.status else payload["status"])
        assert len(goal.cadence.split()) == 5
        # research goals carry categories
        assert isinstance(goal.config.get("categories"), list)
        assert len(goal.config["categories"]) >= 1


def test_seed_daily_report_has_six_categories() -> None:
    report = next(g for g in SEED_GOALS if g["title"] == "Daily AI Intelligence Report")
    ids = [c["id"] for c in report["config"]["categories"]]
    assert "claude-code" in ids
    assert len(ids) == 6
