"""Markdown -> docx/pdf deliverables via pandoc."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def _pandoc() -> str:
    found = shutil.which("pandoc")
    if found:
        return found
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "Pandoc" / "pandoc.exe"
    if local.exists():
        return str(local)
    raise FileNotFoundError("pandoc not found - install it (winget install JohnMacFarlane.Pandoc)")


def export_markdown(markdown: str, out_path: str | Path, title: str = "") -> dict:
    """Render markdown text to the format implied by out_path suffix (.docx/.pdf/.html)."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        if title:
            f.write(f"% {title}\n\n")
        f.write(markdown)
        src = f.name
    args = [_pandoc(), src, "-o", str(out), "--standalone"]
    if out.suffix == ".pdf":
        # wkhtmltopdf/latex may be absent; html intermediate keeps deps minimal
        args += ["--pdf-engine=wkhtmltopdf"]
    proc = subprocess.run(args, capture_output=True, text=True, timeout=300)
    return {"ok": proc.returncode == 0 and out.exists(), "path": str(out),
            "stderr": proc.stderr[-500:] if proc.returncode != 0 else ""}
