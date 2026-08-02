# LangChain ecosystem: ALWAYS load the relevant skills before doing ANYTHING with LangChain code

The LangChain ecosystem (langchain, langchain-core, langchain-anthropic, langgraph, deepagents) evolves fast — function locations, class signatures, and patterns move between minor versions. Guessing any of it is how you ship something that passes lint but blows up the first time a user hits an endpoint.

## The rule

**Before doing ANYTHING with LangChain/langgraph/deepagents code — reading, writing, editing, fixing, reviewing, or debugging — you MUST load the relevant skill(s) first.**.

1. Load the skill(s) for the subsystem you're touching:
   - `/langchain-fundamentals` — agents, tools, middleware, `create_agent`, model construction
   - `/langchain-dependencies` — what's installed, version constraints
   - `/langchain-middleware` — middleware patterns
   - `/langchain-rag` — RAG/vector-store patterns
   - `/langgraph-fundamentals` — graphs, state, checkpointers
   - `/deep-agents-core` — deep agent framework (this project's orchestrator is built on it)
2. Only then touch the code.

## Known landmines (this repo, verified 2026-08-02)

| Wrong (blows up at runtime) | Correct |
|---|---|
| `from langchain_core.language_models.chat_models import init_chat_model` | `from langchain.chat_models import init_chat_model` |

The model-agnostic constructor `init_chat_model()` lives in **`langchain.chat_models`**, NOT in `langchain_core`. `langchain_core.language_models.chat_models` has no such name — it imports cleanly by accident and fails only when the agent graph calls `_model()`.
