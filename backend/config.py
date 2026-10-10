"""Model, paths, and cost limits for the Campus Customs agent team.

Every agent uses gpt-6-luna through Portkey. The model name is fixed here on purpose: there is no
environment override, so no agent can end up on a different (more expensive) model.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import UsageLimits
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

BACKEND = Path(__file__).resolve().parent
HW5 = BACKEND.parent
PROMPTS_DIR = BACKEND / "prompts"
MCP_SERVER = HW5 / "mcp_server" / "server.py"
# CAMPUS_AUDIT_PATH lets test runs write to a scratch trail so the real one only holds real runs.
AUDIT_TRAIL = Path(os.getenv("CAMPUS_AUDIT_PATH") or HW5 / "output" / "audit_trail.json")
ORIGINAL_DB = HW5 / "data" / "campus_customs.db"       # never written; the reset source

# The nearest .env wins: hw5/.env first, then the folders above it.
for folder in (HW5, *HW5.parents[:2]):
    if (folder / ".env").exists():
        load_dotenv(folder / ".env", override=False)

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")  # keep stdout clean

MODEL_NAME = "gpt-6-luna"  # the only model allowed for this homework, for every agent
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# ---- Cost limits (one ticket run = the Boss plus every teammate it pulls in) ----
# All agents in a run share one usage counter, so these caps cover the whole team, not each agent.
TICKET_USAGE_LIMITS = UsageLimits(
    request_limit=40,           # model calls across all agents in one ticket run
    tool_calls_limit=60,        # MCP + delegation calls across all agents
    total_tokens_limit=300_000,
)
MAX_DELEGATION_DEPTH = 3        # Boss -> A -> B -> C is the deepest a hand-off chain can go
MAX_DELEGATIONS_PER_TICKET = 10
MODEL_SETTINGS = OpenAIResponsesModelSettings(max_tokens=6000, timeout=120)


def working_db() -> Path:
    """The database the MCP server works on: the working copy, or CAMPUS_DB_PATH for test runs."""
    return Path(os.getenv("CAMPUS_DB_PATH") or HW5 / "data" / "campus_customs_new.db")


def mcp_server_env() -> dict[str, str]:
    """Environment for the MCP server process: just enough to run, and no API keys."""
    env = {k: os.environ[k] for k in ("PATH", "HOME") if k in os.environ}
    if os.getenv("CAMPUS_DB_PATH"):
        env["CAMPUS_DB_PATH"] = os.environ["CAMPUS_DB_PATH"]
    return env


def require_api_key() -> str:
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set. Put it in hw5/.env (see .env.example).")
    return key


@lru_cache(maxsize=1)
def build_model() -> OpenAIResponsesModel:
    """One shared gpt-6-luna model object for all five agents.

    Responses API, not Chat Completions: Portkey routes gpt-6-luna to a backend that rejects
    function tools on /v1/chat/completions (found in Lecture 10).
    """
    client = AsyncOpenAI(api_key=require_api_key(), base_url=PORTKEY_BASE_URL, timeout=120.0, max_retries=2)
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


def load_prompt(agent: str) -> str:
    return (PROMPTS_DIR / f"{agent}.md").read_text(encoding="utf-8").strip()
