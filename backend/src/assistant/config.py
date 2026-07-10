"""Central configuration. All values overridable via environment / .env."""

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ASSISTANT_", extra="ignore")

    # --- LLM (model-agnostic via LangChain provider strings) ---
    default_model: str = "ollama:glm-5.2:cloud"
    ollama_base_url: str = "http://localhost:11434"
    embedding_model: str = "bge-m3"

    # --- Claude Code bridge ---
    # CC instances talk to Ollama's Anthropic-compatible endpoint, not Anthropic.
    cc_anthropic_base_url: str = "http://localhost:11434"
    cc_model: str = "glm-5.2:cloud"
    cc_max_review_iterations: int = 3
    cc_hooks_webhook_path: str = "/api/cc-runs/hooks"
    # Directory of local CC plugins passed to delegated sessions via the SDK
    # (user-scope plugin installs are invisible with setting_sources=["project"]).
    # Each subdir with .claude-plugin/plugin.json is loaded. "" = no plugins.
    cc_plugins_dir: str = ""

    # --- Persistence ---
    # Host port 5433: 5432 is occupied by the local langfuse stack's Postgres.
    database_url: str = "postgresql://assistant:assistant@localhost:5433/assistant"
    qdrant_url: str = "http://localhost:6333"

    # --- Paths ---
    vault_path: str = ""  # markdown vault to watch/ingest; empty = disabled
    examples_path: str = ""  # where uploaded reference examples are stored; "" = disabled

    # --- API ---
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # --- Native CC memory bridge ---
    # When true, record_decision/write_convention also append to the target
    # repo's .claude/rules/*.md so CC sessions see them natively next run.
    write_project_rules: bool = True

    # --- LangSmith tracing (bare LANGSMITH_* names, read from .env / env) ---
    # The tracer itself reads these from os.environ; we push them there at startup.
    langsmith_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("ASSISTANT_LANGSMITH_API_KEY", "LANGSMITH_API_KEY"))
    langsmith_tracing: str = Field(
        default="false",
        validation_alias=AliasChoices("ASSISTANT_LANGSMITH_TRACING", "LANGSMITH_TRACING"))
    langsmith_project: str = Field(
        default="bitch-stewie",
        validation_alias=AliasChoices("ASSISTANT_LANGSMITH_PROJECT", "LANGSMITH_PROJECT"))
    langsmith_endpoint: str = Field(
        default="https://api.smith.langchain.com",
        validation_alias=AliasChoices("ASSISTANT_LANGSMITH_ENDPOINT", "LANGSMITH_ENDPOINT"))


@lru_cache
def get_settings() -> Settings:
    return Settings()


def langsmith_enabled() -> bool:
    s = get_settings()
    return bool(s.langsmith_api_key) and s.langsmith_tracing.lower() == "true"


def apply_langsmith_env() -> bool:
    """Push LANGSMITH_* into os.environ before langchain/langgraph import tracing.

    Returns True if tracing is enabled. Idempotent.
    """
    import os
    s = get_settings()
    if not langsmith_enabled():
        # Ensure a stale env var can't silently enable tracing
        os.environ.pop("LANGSMITH_TRACING", None)
        return False
    os.environ["LANGSMITH_API_KEY"] = s.langsmith_api_key
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = s.langsmith_project
    os.environ.setdefault("LANGSMITH_ENDPOINT", s.langsmith_endpoint)
    return True
