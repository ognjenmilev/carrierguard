"""CarrierGuard FMCSA MCP server.

Exposes FMCSA carrier lookup as an MCP tool so the ADK agent — or any MCP
client — can fetch normalized carrier data. Runs over stdio (the default
transport), which is how the ADK agent connects to it as a subprocess.

Kept out of the ``app`` package on purpose: it only needs ``core`` + ``mcp``,
not ADK or GCP credentials, so it stays lightweight and independently runnable.
"""

from __future__ import annotations

from dataclasses import asdict

from mcp.server.fastmcp import FastMCP

from core.fmcsa.client import fetch_carrier

mcp = FastMCP("carrierguard-fmcsa")


@mcp.tool()
def lookup_carrier(mc_number: str) -> dict:
    """Look up a freight carrier by its MC (docket) number from live FMCSA data.

    Args:
        mc_number: The carrier's MC / docket number (digits, with or without an
            "MC" prefix).

    Returns:
        Normalized carrier fields: legal_name, dot_number, authority_status
        (ACTIVE/INACTIVE), insurance_on_file, insurance_required, safety_rating,
        out_of_service, physical_address, plus the raw FMCSA payload.
    """
    return asdict(fetch_carrier(mc_number))


if __name__ == "__main__":
    mcp.run()
