"""Jobs/delegation service facade.

Re-exports the queue, vault-watcher, and delegation-runner entry points the
interface layer needs, so routers/CLI never import `assistant.infrastructure.jobs`
or `assistant.infrastructure.cc_bridge` directly.
"""

from assistant.infrastructure.cc_bridge.brief import Brief
from assistant.infrastructure.cc_bridge.runner import DelegationRunner
from assistant.infrastructure.jobs.queue import app as job_app
from assistant.infrastructure.jobs.queue import delegate_brief
from assistant.infrastructure.jobs.watcher import watch_vault

__all__ = [
    "Brief",
    "DelegationRunner",
    "delegate_brief",
    "job_app",
    "watch_vault",
]
