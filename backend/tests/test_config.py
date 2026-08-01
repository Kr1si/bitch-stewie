import os
from unittest import mock

from assistant.shared import config
from assistant.shared.config import Settings, apply_langsmith_env, langsmith_enabled


def test_default_model_is_longcat() -> None:
    """The orchestrator/planner default LLM is LongCat (Story 10).

    Resolved by deepagents via init_chat_model('anthropic:LongCat-2.0'), which
    routes through ANTHROPIC_BASE_URL + ANTHROPIC_API_KEY in docker-compose.
    """
    settings = Settings()
    assert settings.default_model == "anthropic:LongCat-2.0"


def test_longcat_default_does_not_require_env(monkeypatch) -> None:
    """A fresh Settings() with no env exposes LongCat without reading ANTHROPIC_*.

    init_chat_model reads those at call time, not at construction — so merely
    building Settings must not fail when they are absent.
    """
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    settings = Settings()
    assert settings.default_model == "anthropic:LongCat-2.0"


def test_cc_provider_code_defaults_to_ollama_local() -> None:
    """CC provider CODE-defaults to local Ollama; compose overrides to LongCat.

    The Python default stays Ollama (so a bare `uv run` works offline); the
    LongCat default for production lives in docker-compose.prod.yml. This test
    guards the code-side default so the two don't silently drift. The project's
    own .env (gitignored) sets the LongCat key, so build Settings with the env
    file disabled to read the true code defaults.
    """
    settings = Settings(_env_file=None)
    assert settings.cc_anthropic_base_url == "http://localhost:11434"
    assert settings.cc_anthropic_auth_token == "ollama"
    assert settings.cc_model == "glm-5.2:cloud"


def test_langsmith_disabled_without_key() -> None:
    with mock.patch.dict(os.environ, {}, clear=True):
        # Rebuild Settings from the now-empty environment.
        config.get_settings.cache_clear()
        try:
            assert langsmith_enabled() is False
        finally:
            config.get_settings.cache_clear()


def test_langsmith_disabled_without_tracing(monkeypatch) -> None:
    monkeypatch.setenv("ASSISTANT_LANGSMITH_API_KEY", "sk-test-key")
    monkeypatch.setenv("ASSISTANT_LANGSMITH_TRACING", "false")
    config.get_settings.cache_clear()
    try:
        assert langsmith_enabled() is False
    finally:
        config.get_settings.cache_clear()


def test_langsmith_enabled_requires_both(monkeypatch) -> None:
    monkeypatch.setenv("ASSISTANT_LANGSMITH_API_KEY", "sk-test-key")
    monkeypatch.setenv("ASSISTANT_LANGSMITH_TRACING", "true")
    config.get_settings.cache_clear()
    try:
        assert langsmith_enabled() is True
    finally:
        config.get_settings.cache_clear()


def test_apply_langsmith_env_pushes_to_environ(monkeypatch) -> None:
    monkeypatch.setenv("ASSISTANT_LANGSMITH_API_KEY", "sk-test-key")
    monkeypatch.setenv("ASSISTANT_LANGSMITH_TRACING", "true")
    monkeypatch.setenv("ASSISTANT_LANGSMITH_PROJECT", "my-proj")
    config.get_settings.cache_clear()
    try:
        assert apply_langsmith_env() is True
        assert os.environ["LANGSMITH_API_KEY"] == "sk-test-key"
        assert os.environ["LANGSMITH_TRACING"] == "true"
        assert os.environ["LANGSMITH_PROJECT"] == "my-proj"
    finally:
        config.get_settings.cache_clear()


def test_apply_langsmith_env_is_idempotent(monkeypatch) -> None:
    monkeypatch.setenv("ASSISTANT_LANGSMITH_API_KEY", "sk-test-key")
    monkeypatch.setenv("ASSISTANT_LANGSMITH_TRACING", "true")
    config.get_settings.cache_clear()
    try:
        apply_langsmith_env()
        apply_langsmith_env()
        assert os.environ["LANGSMITH_API_KEY"] == "sk-test-key"
    finally:
        config.get_settings.cache_clear()


def test_review_iterations_default() -> None:
    assert Settings().cc_max_review_iterations == 3
