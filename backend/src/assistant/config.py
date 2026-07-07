"""Central configuration. All values overridable via environment / .env."""

from functools import lru_cache

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
