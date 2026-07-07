"""LikeC4 -> draw.io export pipeline. The LikeC4 model is the source of truth."""

import subprocess
from pathlib import Path


def find_model_dir(repo_path: str) -> Path | None:
    """Locate the directory containing .likec4/.c4 model files in a repo."""
    root = Path(repo_path)
    for candidate in (root / "likec4", root / "architecture", root):
        if candidate.is_dir() and any(candidate.glob("*.likec4")) or any(candidate.glob("*.c4")):
            return candidate
    hits = list(root.rglob("*.likec4"))[:1] or list(root.rglob("*.c4"))[:1]
    return hits[0].parent if hits else None


def export_drawio(model_dir: str | Path, out_dir: str | Path) -> dict:
    """Run `likec4 export drawio` and return the produced files."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["npx", "--yes", "likec4", "export", "drawio", "--uncompressed",
         "--outdir", str(out), str(model_dir)],
        capture_output=True, text=True, timeout=600, shell=(True if _needs_shell() else False),
    )
    files = sorted(str(p) for p in out.glob("*.drawio"))
    return {
        "ok": proc.returncode == 0 and bool(files),
        "files": files,
        "stderr": proc.stderr[-1000:] if proc.returncode != 0 else "",
    }


def _needs_shell() -> bool:
    import sys

    return sys.platform == "win32"  # npx is npx.cmd on Windows
