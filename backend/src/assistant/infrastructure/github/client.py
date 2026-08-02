"""GitHub operations via the ``gh`` CLI.

Wraps ``gh`` subcommands with subprocess so the rest of the codebase has one
place to go for GitHub. Every call inherits the CLI's configured auth — no
token handling here.
"""

import json
import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def _gh(args: list[str], timeout: float = 60) -> tuple[int, str, str]:
    """Run a ``gh`` command, returning (returncode, stdout, stderr)."""
    proc = subprocess.run(
        ["gh", *args], capture_output=True, text=True, timeout=timeout,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def parse_git_url(url: str) -> tuple[str, str]:
    """Parse a git URL into (owner, repo).

    Accepts:
      - https://github.com/owner/repo(.git)
      - git@github.com:owner/repo(.git)
      - owner/repo (shorthand)

    Raises:
        ValueError: the input is not a recognizable GitHub repo reference.
    """
    url = url.strip().rstrip("/")
    # owner/repo shorthand
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", url):
        owner, repo = url.split("/", 1)
        return owner, repo
    # https://github.com/owner/repo(.git)
    m = re.match(r"https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?$", url)
    if m:
        return m.group(1), m.group(2)
    # git@github.com:owner/repo(.git)
    m = re.match(r"git@github\.com:([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?$", url)
    if m:
        return m.group(1), m.group(2)
    raise ValueError(f"not a valid GitHub repo reference: {url!r}")


def owner_repo(owner: str, repo: str) -> str:
    """Canonical ``owner/repo`` string."""
    return f"{owner}/{repo}"


def repo_exists(owner_repo_str: str) -> bool:
    """True if ``owner/repo`` is accessible to the configured gh account."""
    code, _, _ = _gh(["api", f"repos/{owner_repo_str}", "--jq", ".id"],
                     timeout=30)
    return code == 0


def repo_info(owner_repo_str: str) -> dict:
    """Fetch repo metadata via ``gh api``.

    Returns dict with keys: name, full_name, description, default_branch,
    html_url, private. Raises RuntimeError if the repo is not accessible.
    """
    code, out, err = _gh(
        ["api", f"repos/{owner_repo_str}",
         "--jq", "{name,full_name,description,default_branch,html_url,private}"],
        timeout=30,
    )
    if code != 0:
        raise RuntimeError(f"could not read repo {owner_repo_str}: {err}")
    return json.loads(out)


def clone_repo(owner_repo_str: str, dest: Path, timeout: float = 300) -> Path:
    """Clone ``owner/repo`` into ``dest`` via ``gh repo clone``.

    ``dest`` is the directory the repo lands in (its ``.git`` will be at
    ``dest/.git``). If ``dest`` already exists and is a git repo, it is reused
    as-is instead of erroring. Returns the resolved repo directory.
    """
    dest = Path(dest)
    if dest.is_dir() and (dest / ".git").is_dir():
        logger.info("repo already cloned at %s; reusing", dest)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    code, out, err = _gh(
        ["repo", "clone", owner_repo_str, str(dest), "--", "--depth", "1"],
        timeout=timeout,
    )
    if code != 0:
        raise RuntimeError(f"could not clone {owner_repo_str}: {err or out}")
    return dest
