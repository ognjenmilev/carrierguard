"""CarrierGuard core domain logic.

Pure, dependency-free building blocks (data models, FMCSA client, fraud
heuristics, scoring, records). Deliberately free of ADK/GCP imports so the
unit tests run fast and without cloud credentials. The ADK agents in ``app/``
import from here.
"""
