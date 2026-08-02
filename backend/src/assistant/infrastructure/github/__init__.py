"""Unified GitHub access via the ``gh`` CLI.

All GitHub interaction (validation, metadata, cloning) goes through the ``gh``
command so auth, protocol and scoping stay in one place — the CLI is already
configured with credentials on the host. Anything that needs GitHub talks to
:func:`client.repo_info` / :func:`client.clone_repo`; never call the REST API
directly.
"""

from assistant.infrastructure.github.client import (
    clone_repo,
    owner_repo,
    parse_git_url,
    repo_exists,
    repo_info,
)

__all__ = [
    "clone_repo",
    "owner_repo",
    "parse_git_url",
    "repo_exists",
    "repo_info",
]
