# ruff: noqa
"""CarrierGuard ADK agent.

A single LlmAgent that vets a freight carrier end to end:
  1. calls `lookup_carrier` (served over MCP by mcp_server.server) for live FMCSA data,
  2. calls the deterministic `assess_carrier` tool to score risk + write the audit record,
  3. reports APPROVE / REVIEW / REJECT with the findings.

The LLM orchestrates and explains; the risk decision itself is computed in code
(see app/tools.py + core/), never by the model.
"""

import os
import sys

import google.auth
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.genai import types
from mcp import StdioServerParameters

from app.tools import assess_carrier

# Load .env (FMCSA_WEBKEY, etc.) for both this process and the MCP subprocess.
load_dotenv()

# Use Gemini via Vertex with the user's gcloud application-default credentials.
_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The FMCSA MCP server, launched as a stdio subprocess (real MCP integration).
fmcsa_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server.server"],
            cwd=_REPO_ROOT,
            env={**os.environ, "PYTHONPATH": _REPO_ROOT},
        ),
        timeout=30,
    ),
    tool_filter=["lookup_carrier"],
)

INSTRUCTION = """You are CarrierGuard, an assistant that vets freight carriers for brokers.

When the user gives you a carrier's MC number (optionally with the carrier name from the rate confirmation):
1. Call `lookup_carrier` with the MC number to pull the carrier's live FMCSA data.
2. Call `assess_carrier`, passing the carrier data from step 1 exactly as returned (and the rate-confirmation name if the user gave one).
3. Report the result clearly:
   - The decision on its own line in capitals: APPROVE, REVIEW, or REJECT.
   - The risk score out of 100.
   - Each finding as a bullet: [SEVERITY] detail.
   - The audit record id.

Only state facts the tools returned — never invent carrier details. If a tool errors, say so plainly.
Always end with: "This supports due diligence and is not legal advice."
"""

root_agent = LlmAgent(
    name="carrierguard",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=INSTRUCTION,
    tools=[fmcsa_toolset, assess_carrier],
)

app = App(
    root_agent=root_agent,
    name="app",
)
