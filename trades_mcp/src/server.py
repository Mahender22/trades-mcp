"""TradesMCP — Permits, Licenses & Pricing Data for AI Assistants.

FastMCP server providing construction/trades profession data:
- Contractor license verification (CA, TX, FL, NY)
- Building permit search
- Material pricing
- BLS labor rates
- Project cost estimation
- Compliance tracking
"""

from typing import Optional

from fastmcp import FastMCP

from . import config
from .models import (
    SUPPORTED_STATES,
    LICENSE_CLASSIFICATIONS,
    INSURANCE_REQUIREMENTS,
    BOND_REQUIREMENTS,
)

mcp = FastMCP(
    name="Trades MCP Server",
    instructions=(
        "You are connected to a trades profession data MCP server. "
        "Use these tools to look up contractor licenses, search building permits, "
        "get material pricing, labor rates, and compliance information for the "
        "construction industry. Covers CA, TX, FL, and NY."
    ),
)


# ==========================================================================
# Tier 1 — License & Permits (Starter)
# ==========================================================================


@mcp.tool
async def verify_contractor_license(state: str, license_number: str) -> dict:
    """Check a contractor's license status by state and license number.

    Args:
        state: Two-letter state code (CA, TX, FL, NY)
        license_number: The contractor's license number (e.g., "1098765" for CA)

    Returns:
        License details including name, status, classification, expiration, bond, and workers comp info.
    """
    from .licenses import verify_license

    try:
        result = await verify_license(state, license_number)
        return {"status": "success", "license": result.to_dict()}
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except ConnectionError as e:
        return {"status": "error", "message": str(e)}


@mcp.tool
async def search_contractor_by_name(
    state: str,
    name: str,
    classification: Optional[str] = None,
    city: Optional[str] = None,
) -> dict:
    """Find contractors and their license info by name.

    Args:
        state: Two-letter state code (CA, TX, FL, NY)
        name: Contractor name or business name to search
        classification: Optional license classification filter (e.g., "B", "C-10")
        city: Optional city filter

    Returns:
        List of matching contractor licenses.
    """
    from .licenses import search_by_name

    try:
        results = await search_by_name(state, name, classification=classification, city=city)
        return {
            "status": "success",
            "count": len(results),
            "results": [r.to_dict() for r in results],
        }
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except ConnectionError as e:
        return {"status": "error", "message": str(e)}


@mcp.tool
async def check_license_expiration(state: str, license_number: str) -> dict:
    """Get expiration dates and renewal requirements for a contractor license.

    Args:
        state: Two-letter state code (CA, TX, FL, NY)
        license_number: The contractor's license number

    Returns:
        Expiration date, status, and renewal guidance.
    """
    from .licenses import verify_license

    try:
        lic = await verify_license(state, license_number)
        state_info = SUPPORTED_STATES.get(state.upper(), {})

        result = {
            "license_number": lic.license_number,
            "state": lic.state,
            "name": lic.name,
            "status": lic.status,
            "expiration_date": lic.expiration_date,
        }

        # Add renewal guidance
        if lic.status and "active" in lic.status.lower():
            result["renewal_status"] = "Current — no action needed"
        elif lic.status and "inactive" in lic.status.lower():
            result["renewal_status"] = "INACTIVE — renewal required to continue work"
        elif lic.status and "expired" in lic.status.lower():
            result["renewal_status"] = "EXPIRED — must renew before performing any licensed work"
        else:
            result["renewal_status"] = "Check with licensing board"

        if state_info.get("notes"):
            result["state_notes"] = state_info["notes"]

        result["renewal_url"] = state_info.get("url", "Check your state licensing board")

        return {"status": "success", "expiration": result}
    except (ValueError, ConnectionError) as e:
        return {"status": "error", "message": str(e)}


@mcp.tool
async def search_building_permits(
    address: Optional[str] = None,
    contractor_name: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    permit_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> dict:
    """Search building permits by address, contractor, date, or type.

    Args:
        address: Street address to search
        contractor_name: Contractor name on the permit
        city: City name (e.g., "Los Angeles")
        state: Two-letter state code
        permit_type: Type of permit (e.g., "Building", "Electrical", "Plumbing")
        date_from: Start date filter (YYYY-MM-DD)
        date_to: End date filter (YYYY-MM-DD)

    Returns:
        List of matching building permits.
    """
    from .permits import search_permits

    try:
        results = await search_permits(
            address=address,
            contractor_name=contractor_name,
            permit_type=permit_type,
            city=city,
            state=state,
            date_from=date_from,
            date_to=date_to,
        )
        return {
            "status": "success",
            "count": len(results),
            "permits": [p.to_dict() for p in results],
        }
    except ConnectionError as e:
        return {"status": "error", "message": str(e)}


@mcp.tool
async def get_permit_details(
    permit_number: str,
    city: Optional[str] = None,
    state: Optional[str] = None,
) -> dict:
    """Get full details for a specific building permit including inspections.

    Args:
        permit_number: The permit number to look up
        city: City where the permit was issued
        state: Two-letter state code

    Returns:
        Full permit record with type, status, valuation, and inspection history.
    """
    from .permits import get_permit_details as _get_detail

    try:
        result = await _get_detail(permit_number, city=city, state=state)
        return {"status": "success", "permit": result.to_dict()}
    except ConnectionError as e:
        return {"status": "error", "message": str(e)}


@mcp.tool
def list_supported_states() -> dict:
    """List all states currently supported for license verification.

    Returns:
        Supported states with licensing board info, lookup URLs, and license formats.
    """
    states = []
    for code, info in SUPPORTED_STATES.items():
        states.append({
            "code": code,
            "name": info["name"],
            "board": info["board"],
            "lookup_url": info["lookup_url"],
            "license_format": info["license_format"],
            "notes": info.get("notes", ""),
        })

    return {
        "status": "success",
        "count": len(states),
        "states": states,
        "classifications": {
            "description": "California license classifications (most comprehensive system)",
            "classifications": LICENSE_CLASSIFICATIONS,
        },
    }


# ==========================================================================
# Tier 2 — Pricing & Rates (Pro)
# ==========================================================================


def _check_pro_tier() -> Optional[dict]:
    """Check if the current tier allows Pro features."""
    if config.TIER == "starter":
        return {
            "status": "error",
            "message": "This feature requires the Pro plan ($49/mo). Upgrade at https://mcpize.com",
        }
    return None


@mcp.tool
async def get_material_prices(
    material: Optional[str] = None,
    category: Optional[str] = None,
) -> dict:
    """Get current pricing for common construction materials.

    Args:
        material: Specific material to search (e.g., "copper pipe", "lumber 2x4")
        category: Material category: lumber, plumbing, electrical, concrete,
                  insulation, roofing, paint, hvac, drywall

    Returns:
        Material prices with units, trends, and last-updated dates.
    """
    tier_check = _check_pro_tier()
    if tier_check:
        return tier_check

    from .pricing import get_material_prices as _get_prices

    results = await _get_prices(material=material, category=category)
    return {
        "status": "success",
        "count": len(results),
        "prices": [m.to_dict() for m in results],
        "note": "Prices are typical retail/contractor pricing. Actual prices vary by region, supplier, and volume.",
    }


@mcp.tool
async def get_labor_rates(
    trade: str,
    region: Optional[str] = None,
) -> dict:
    """Get BLS labor rates by trade and region.

    Args:
        trade: Trade name (electrician, plumber, hvac, carpenter, painter, roofer,
               mason, welder, general_contractor, sheet_metal, insulation, concrete)
        region: Optional metro area (los angeles, san francisco, new york, houston,
                dallas, chicago, miami, phoenix, seattle, denver, atlanta, boston)

    Returns:
        Hourly rate, annual salary, and source information.
    """
    tier_check = _check_pro_tier()
    if tier_check:
        return tier_check

    from .pricing import get_labor_rates as _get_rates

    try:
        result = await _get_rates(trade, region=region)
        return {"status": "success", "rate": result.to_dict()}
    except ValueError as e:
        return {"status": "error", "message": str(e)}


@mcp.tool
def estimate_project_cost(
    description: str,
    square_feet: Optional[float] = None,
    trade: Optional[str] = None,
    region: Optional[str] = None,
) -> dict:
    """Generate a rough project cost estimate from a description.

    Args:
        description: Project description (e.g., "kitchen remodel", "roof replacement",
                     "electrical rewire", "bathroom renovation")
        square_feet: Project area in square feet (defaults to 1000 if not provided)
        trade: Primary trade involved
        region: Metro area for regional pricing adjustment

    Returns:
        Low/mid/high cost estimates with methodology notes.
    """
    tier_check = _check_pro_tier()
    if tier_check:
        return tier_check

    from .pricing import estimate_project_cost as _estimate

    result = _estimate(
        description=description,
        square_feet=square_feet,
        trade=trade,
        region=region,
    )
    return {"status": "success", **result}


@mcp.tool
def compare_regional_costs(
    trade: str,
    regions: Optional[list[str]] = None,
) -> dict:
    """Compare labor and material costs across metro areas.

    Args:
        trade: Trade name (electrician, plumber, hvac, carpenter, etc.)
        regions: Optional list of metro areas to compare.
                 If omitted, compares all available metros.

    Returns:
        Ranked list of regions with hourly rates, annual salaries, and cost index.
    """
    tier_check = _check_pro_tier()
    if tier_check:
        return tier_check

    from .pricing import compare_regional_costs as _compare

    try:
        results = _compare(trade, regions=regions)
        return {
            "status": "success",
            "trade": trade,
            "count": len(results),
            "comparison": results,
        }
    except ValueError as e:
        return {"status": "error", "message": str(e)}


# ==========================================================================
# Tier 3 — Compliance (Pro)
# ==========================================================================


@mcp.tool
def check_insurance_requirements(state: str) -> dict:
    """Get workers comp, general liability, and insurance requirements by state.

    Args:
        state: Two-letter state code (CA, TX, FL, NY)

    Returns:
        Workers comp requirements, general liability info, bond requirements, and state-specific notes.
    """
    tier_check = _check_pro_tier()
    if tier_check:
        return tier_check

    state = state.upper()
    if state not in INSURANCE_REQUIREMENTS:
        return {
            "status": "error",
            "message": f"State '{state}' not yet supported. Supported: {', '.join(INSURANCE_REQUIREMENTS.keys())}",
        }

    return {
        "status": "success",
        "state": state,
        "requirements": INSURANCE_REQUIREMENTS[state],
    }


@mcp.tool
def get_bond_requirements(state: str) -> dict:
    """Get bid bond, performance bond, and contractor license bond requirements.

    Args:
        state: Two-letter state code (CA, TX, FL, NY)

    Returns:
        Bond types and amounts required for the state.
    """
    tier_check = _check_pro_tier()
    if tier_check:
        return tier_check

    state = state.upper()
    if state not in BOND_REQUIREMENTS:
        return {
            "status": "error",
            "message": f"State '{state}' not yet supported. Supported: {', '.join(BOND_REQUIREMENTS.keys())}",
        }

    return {
        "status": "success",
        "state": state,
        "bonds": BOND_REQUIREMENTS[state],
    }


@mcp.tool
async def track_compliance_deadlines(state: str, license_number: str) -> dict:
    """Track upcoming expirations and renewal deadlines for a contractor.

    Args:
        state: Two-letter state code (CA, TX, FL, NY)
        license_number: The contractor's license number

    Returns:
        Upcoming deadlines for license renewal, bond renewal, insurance, and continuing education.
    """
    tier_check = _check_pro_tier()
    if tier_check:
        return tier_check

    from .licenses import verify_license

    try:
        lic = await verify_license(state, license_number)
    except (ValueError, ConnectionError) as e:
        return {"status": "error", "message": str(e)}

    state_upper = state.upper()
    insurance = INSURANCE_REQUIREMENTS.get(state_upper, {})
    bonds = BOND_REQUIREMENTS.get(state_upper, {})

    deadlines = []

    # License expiration
    if lic.expiration_date:
        deadlines.append({
            "type": "License Renewal",
            "deadline": lic.expiration_date,
            "description": f"Contractor license {lic.license_number} expires {lic.expiration_date}",
            "action": f"Renew at {SUPPORTED_STATES.get(state_upper, {}).get('url', 'state licensing board')}",
        })

    # Workers comp
    if insurance.get("workers_comp"):
        deadlines.append({
            "type": "Workers Compensation",
            "deadline": "Check policy expiration",
            "description": insurance["workers_comp"],
            "action": "Verify current workers comp certificate is on file with licensing board",
        })

    # Bond
    if bonds.get("contractor_license_bond"):
        deadlines.append({
            "type": "License Bond",
            "deadline": "Annually (check your surety company)",
            "description": f"License bond required: {bonds['contractor_license_bond']}",
            "action": "Verify bond is current and meets state requirements",
        })

    # State-specific compliance notes
    state_info = SUPPORTED_STATES.get(state_upper, {})
    if state_info.get("notes"):
        deadlines.append({
            "type": "Regulatory Update",
            "deadline": "Review now",
            "description": state_info["notes"],
            "action": "Check licensing board website for latest requirements",
        })

    return {
        "status": "success",
        "contractor": lic.name,
        "license_number": lic.license_number,
        "state": state_upper,
        "current_status": lic.status,
        "deadlines": deadlines,
    }


# ==========================================================================
# Resources
# ==========================================================================


@mcp.resource("trades://states/supported")
def supported_states_resource() -> str:
    """Reference: all supported states and their licensing board info."""
    lines = ["# Supported States for TradesMCP\n"]
    for code, info in SUPPORTED_STATES.items():
        lines.append(f"## {info['name']} ({code})")
        lines.append(f"- Board: {info['board']}")
        lines.append(f"- Lookup: {info['lookup_url']}")
        lines.append(f"- Format: {info['license_format']}")
        if info.get("notes"):
            lines.append(f"- Notes: {info['notes']}")
        lines.append("")
    return "\n".join(lines)


@mcp.resource("trades://classifications/california")
def ca_classifications_resource() -> str:
    """Reference: California contractor license classifications."""
    lines = ["# California Contractor License Classifications\n"]
    for code, desc in sorted(LICENSE_CLASSIFICATIONS.items()):
        lines.append(f"- **{code}**: {desc}")
    return "\n".join(lines)


@mcp.resource("trades://pricing/materials")
def materials_resource() -> str:
    """Reference: current material pricing catalog."""
    from .pricing import MATERIAL_PRICES

    lines = ["# Construction Material Pricing (March 2026)\n"]
    for key, mat in MATERIAL_PRICES.items():
        trend = {"up": "↑", "down": "↓", "stable": "→"}.get(mat.price_trend, "")
        lines.append(f"- **{mat.material}**: ${mat.price:.2f} {mat.unit} {trend}")
    return "\n".join(lines)


@mcp.resource("trades://labor/rates")
def labor_rates_resource() -> str:
    """Reference: national average labor rates by trade."""
    from .pricing import FALLBACK_LABOR_RATES

    lines = ["# National Average Labor Rates by Trade (BLS OEWS)\n"]
    for key, rate in sorted(FALLBACK_LABOR_RATES.items(), key=lambda x: x[1].hourly_rate, reverse=True):
        lines.append(f"- **{rate.trade}**: ${rate.hourly_rate:.2f}/hr (${rate.annual_salary:,.0f}/yr)")
    return "\n".join(lines)


# ==========================================================================
# Entry point
# ==========================================================================


def main():
    try:
        mcp.run()
    except KeyboardInterrupt:
        pass
