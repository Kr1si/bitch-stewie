"""Host-side helpers. The backend runs on the user's machine, so it can pop a
real native OS folder dialog and return the absolute path — something a browser
file input is deliberately not allowed to do (it can only hand back sandboxed
relative paths). The web UI's "Browse..." button calls this endpoint."""

import asyncio
import threading

from fastapi import APIRouter

router = APIRouter(prefix="/api/util")


def _pick_folder_sync(title: str = "Select project repository",
                      initialdir: str = "") -> str | None:
    """Open the native folder picker and block until the user chooses (or cancels).

    Tk is not thread-safe and the server's worker threads are not Tk-friendly,
    so we run the whole create/pick/destroy sequence on its own short-lived
    thread. askdirectory runs its own modal loop and returns without needing
    root.mainloop().

    Headless deployments (docker) have no display or Tk at all — there the
    import fails and the endpoint just returns null, same as a cancel.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return None

    box: list[str | None] = []

    def _run() -> None:
        root = tk.Tk()
        root.withdraw()
        try:
            root.attributes("-topmost", True)
        except tk.TclError:
            pass  # not every platform supports -topmost
        path = filedialog.askdirectory(title=title, initialdir=initialdir or None)
        box.append(path)
        root.destroy()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join()
    return box[0] if box else None


@router.get("/pick-folder")
async def pick_folder(initialdir: str = ""):
    """Return the chosen absolute path, or null if the user cancelled."""
    path = await asyncio.to_thread(_pick_folder_sync, initialdir=initialdir)
    return {"path": path}