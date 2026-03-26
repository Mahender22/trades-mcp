"""Configuration — all settings from environment variables."""

import os

# Demo mode: returns cached data without hitting real APIs
DEMO_MODE = os.environ.get("TRADES_MCP_DEMO", "").lower() in ("1", "true", "yes")

# CSLB (California State License Board)
CSLB_BASE_URL = "https://www.cslb.ca.gov/OnlineServices/CheckLicenseII"

# Texas TDLR
TDLR_BASE_URL = "https://www.tdlr.texas.gov"

# Florida DBPR
DBPR_BASE_URL = "https://www.myfloridalicense.com/wl11.asp"

# New York DOS
NYDOS_BASE_URL = "https://appext20.dos.ny.gov/nydos"

# BLS (Bureau of Labor Statistics) — free, no key needed
BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data"
BLS_API_KEY = os.environ.get("BLS_API_KEY", "")  # Optional, higher rate limits with key

# Ollama for parsing unstructured state website data
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:8b")

# Pricing tier (controls which tools are available)
TIER = os.environ.get("TRADES_MCP_TIER", "pro").lower()  # "starter" or "pro"
