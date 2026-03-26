# TradesMCP — Permits, Licenses & Pricing Data for AI Assistants

## What Is This
A paid MCP server providing construction/trades profession data to AI assistants. Covers contractor license verification, building permits, material pricing, and labor rates. Targeting MCPize marketplace for distribution and monetization.

## Why This Exists
- 11,000+ MCP servers exist but <5% are monetized
- ZERO competition for trades-specific MCP server
- MCPize proven revenue: PostgreSQL Connector $4,200/mo, AWS Security Auditor $8,500/mo
- MCPize gives 85% revenue share, handles payments/hosting/distribution
- Construction is the most underserved vertical for MCP infrastructure
- 2026 CSLB rule changes create new compliance urgency

## Target Market
- General contractors, electricians, plumbers, HVAC companies
- Construction firms needing compliance tracking
- Real estate professionals checking contractor licenses
- Insurance companies verifying contractor credentials

## Pricing
$29/mo Starter (license lookups + permit search)
$49/mo Pro (+ material pricing + labor rates + priority)

## Architecture
- **Framework**: FastMCP (Python) — same pattern as legal-mcp (18 tools, proven)
- **Data Sources**: State licensing boards (scraping), permit databases, material pricing APIs, BLS labor data
- **Distribution**: MCPize marketplace (85/15 rev share)
- **Deployment**: MCPize hosted OR self-hosted via pip install

## Tools to Build (MVP)

### Tier 1 — License & Permits (Starter)
1. `verify_contractor_license` — Check license status by state + license number
2. `search_contractor_by_name` — Find contractors and their license info
3. `check_license_expiration` — Get expiration dates and renewal requirements
4. `search_building_permits` — Search permits by address/contractor/date
5. `get_permit_details` — Full permit record (type, status, inspections)
6. `list_supported_states` — Which states are covered

### Tier 2 — Pricing & Rates (Pro)
7. `get_material_prices` — Current pricing for common materials (lumber, copper, PVC, etc.)
8. `get_labor_rates` — BLS labor rates by trade and region
9. `estimate_project_cost` — AI-powered rough estimate from description
10. `compare_regional_costs` — Compare costs across metro areas

### Tier 3 — Compliance (Pro)
11. `check_insurance_requirements` — Workers comp / liability requirements by state
12. `get_bond_requirements` — Bid bond and performance bond requirements
13. `track_compliance_deadlines` — Upcoming expirations and renewal dates

## Priority States (Start Here)
1. California (CSLB — largest, 2026 rule changes)
2. Texas (TDLR)
3. Florida (DBPR)
4. New York (DOS)
5. These 4 cover ~65% of contractor license demand

## Technical Stack
- Python 3.10+
- FastMCP for MCP server
- httpx for async HTTP / scraping
- beautifulsoup4 for HTML parsing
- pydantic for data validation

## Reference
- Sister project: `C:\GO-CRAZY\legal-mcp\` — same architecture, 18 tools, 33 tests passing
- Discovery research: `C:\GO-CRAZY\discovery\sprint-2026-03-26.md`
- MCPize docs: https://mcpize.com/developers/monetize-mcp-servers
- Cobalt Intelligence (competitor): covers CA, TX, FL, NY only
- Shovels.ai: has permit API but no MCP server

## Commands
- `pip install -e ".[dev]"` — install in dev mode
- `pytest` — run tests
- `python -m trades_mcp.server` — run MCP server locally

## Environment
- Windows machine with RTX 3090 (24GB VRAM)
- Python 3.10
- Ollama at localhost:11434 (Qwen3.5 9B for parsing unstructured state website data)
