import asyncio
import sys

# psycopg async cannot run on Windows' default ProactorEventLoop.
# NOTE: SelectorEventLoop lacks asyncio subprocess support - the cc_bridge
# (claude-agent-sdk) must therefore run its sessions on a dedicated Proactor
# loop in a worker thread. See src/assistant/cc_bridge/.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
