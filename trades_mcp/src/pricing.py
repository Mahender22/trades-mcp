"""Material pricing, BLS labor rates, and project cost estimation."""

import httpx
from typing import Optional

from . import config
from .models import MaterialPrice, LaborRate


# ---------------------------------------------------------------------------
# BLS Series IDs for construction trades (Occupational Employment & Wage Stats)
# Format: OEUM{area}{industry}{occupation}{datatype}
# ---------------------------------------------------------------------------
BLS_TRADE_SERIES = {
    "electrician": {
        "code": "47-2111",
        "title": "Electricians",
        "series_national": "OEUN000000000000047211103",
    },
    "plumber": {
        "code": "47-2152",
        "title": "Plumbers, Pipefitters, and Steamfitters",
        "series_national": "OEUN000000000000047215203",
    },
    "hvac": {
        "code": "49-9021",
        "title": "Heating, AC, and Refrigeration Mechanics",
        "series_national": "OEUN000000000000049902103",
    },
    "carpenter": {
        "code": "47-2031",
        "title": "Carpenters",
        "series_national": "OEUN000000000000047203103",
    },
    "painter": {
        "code": "47-2141",
        "title": "Painters, Construction and Maintenance",
        "series_national": "OEUN000000000000047214103",
    },
    "roofer": {
        "code": "47-2181",
        "title": "Roofers",
        "series_national": "OEUN000000000000047218103",
    },
    "mason": {
        "code": "47-2021",
        "title": "Brickmasons and Blockmasons",
        "series_national": "OEUN000000000000047202103",
    },
    "welder": {
        "code": "51-4121",
        "title": "Welders, Cutters, Solderers, and Brazers",
        "series_national": "OEUN000000000000051412103",
    },
    "general_contractor": {
        "code": "47-1011",
        "title": "First-Line Supervisors of Construction Trades",
        "series_national": "OEUN000000000000047101103",
    },
    "sheet_metal": {
        "code": "47-2211",
        "title": "Sheet Metal Workers",
        "series_national": "OEUN000000000000047221103",
    },
    "insulation": {
        "code": "47-2131",
        "title": "Insulation Workers",
        "series_national": "OEUN000000000000047213103",
    },
    "concrete": {
        "code": "47-2051",
        "title": "Cement Masons and Concrete Finishers",
        "series_national": "OEUN000000000000047205103",
    },
}

# BLS region codes for metro areas
BLS_METRO_AREAS = {
    "los angeles": "0000031080",
    "san francisco": "0000041860",
    "new york": "0000035620",
    "houston": "0000026420",
    "dallas": "0000019100",
    "chicago": "0000016980",
    "miami": "0000033100",
    "phoenix": "0000038060",
    "seattle": "0000042660",
    "denver": "0000019740",
    "atlanta": "0000012060",
    "boston": "0000014460",
}

# ---------------------------------------------------------------------------
# Material pricing — curated reference data with typical ranges
# Updated periodically from industry sources
# ---------------------------------------------------------------------------
MATERIAL_PRICES = {
    "lumber_2x4": MaterialPrice(
        material="Lumber (2x4x8 Stud Grade)",
        unit="per piece",
        price=3.98,
        price_trend="stable",
        last_updated="2026-03",
    ),
    "lumber_2x6": MaterialPrice(
        material="Lumber (2x6x8 #2)",
        unit="per piece",
        price=6.48,
        price_trend="stable",
        last_updated="2026-03",
    ),
    "plywood_4x8": MaterialPrice(
        material="Plywood (4x8 3/4\" CDX)",
        unit="per sheet",
        price=42.00,
        price_trend="down",
        last_updated="2026-03",
    ),
    "osb_4x8": MaterialPrice(
        material="OSB (4x8 7/16\")",
        unit="per sheet",
        price=18.50,
        price_trend="stable",
        last_updated="2026-03",
    ),
    "copper_pipe_1_2": MaterialPrice(
        material="Copper Pipe (1/2\" Type M, 10ft)",
        unit="per piece",
        price=12.80,
        price_trend="up",
        last_updated="2026-03",
    ),
    "copper_pipe_3_4": MaterialPrice(
        material="Copper Pipe (3/4\" Type M, 10ft)",
        unit="per piece",
        price=22.50,
        price_trend="up",
        last_updated="2026-03",
    ),
    "pvc_pipe_2": MaterialPrice(
        material="PVC Pipe (2\" Schedule 40, 10ft)",
        unit="per piece",
        price=6.98,
        price_trend="stable",
        last_updated="2026-03",
    ),
    "pvc_pipe_4": MaterialPrice(
        material="PVC Pipe (4\" Schedule 40, 10ft)",
        unit="per piece",
        price=14.50,
        price_trend="stable",
        last_updated="2026-03",
    ),
    "romex_14_2": MaterialPrice(
        material="Romex Wire (14/2 NM-B, 250ft)",
        unit="per roll",
        price=75.00,
        price_trend="stable",
        last_updated="2026-03",
    ),
    "romex_12_2": MaterialPrice(
        material="Romex Wire (12/2 NM-B, 250ft)",
        unit="per roll",
        price=98.00,
        price_trend="stable",
        last_updated="2026-03",
    ),
    "concrete_60lb": MaterialPrice(
        material="Concrete Mix (60lb bag)",
        unit="per bag",
        price=5.48,
        price_trend="stable",
        last_updated="2026-03",
    ),
    "concrete_ready_mix": MaterialPrice(
        material="Ready-Mix Concrete",
        unit="per cubic yard",
        price=165.00,
        price_trend="up",
        last_updated="2026-03",
    ),
    "drywall_4x8": MaterialPrice(
        material="Drywall (4x8 1/2\" Regular)",
        unit="per sheet",
        price=12.50,
        price_trend="stable",
        last_updated="2026-03",
    ),
    "insulation_r13": MaterialPrice(
        material="Fiberglass Insulation (R-13, 15\" x 32ft)",
        unit="per roll",
        price=22.00,
        price_trend="stable",
        last_updated="2026-03",
    ),
    "insulation_r30": MaterialPrice(
        material="Fiberglass Insulation (R-30, 15\" x 25ft)",
        unit="per roll",
        price=42.00,
        price_trend="stable",
        last_updated="2026-03",
    ),
    "shingle_architectural": MaterialPrice(
        material="Architectural Shingles (per bundle, ~33 sq ft)",
        unit="per bundle",
        price=36.00,
        price_trend="up",
        last_updated="2026-03",
    ),
    "paint_interior_gallon": MaterialPrice(
        material="Interior Paint (Premium, 1 gallon)",
        unit="per gallon",
        price=45.00,
        price_trend="stable",
        last_updated="2026-03",
    ),
    "paint_exterior_gallon": MaterialPrice(
        material="Exterior Paint (Premium, 1 gallon)",
        unit="per gallon",
        price=55.00,
        price_trend="stable",
        last_updated="2026-03",
    ),
    "rebar_no4": MaterialPrice(
        material="Rebar (#4, 1/2\", 20ft)",
        unit="per piece",
        price=12.00,
        price_trend="stable",
        last_updated="2026-03",
    ),
    "hvac_unit_3ton": MaterialPrice(
        material="Central AC Unit (3-ton, 14 SEER)",
        unit="per unit",
        price=3200.00,
        price_trend="stable",
        last_updated="2026-03",
    ),
}

# Fallback labor rates when BLS API is unavailable
FALLBACK_LABOR_RATES = {
    "electrician": LaborRate(trade="Electrician", region="National Average", hourly_rate=29.61, annual_salary=61590, period="2025"),
    "plumber": LaborRate(trade="Plumber", region="National Average", hourly_rate=30.46, annual_salary=63350, period="2025"),
    "hvac": LaborRate(trade="HVAC Technician", region="National Average", hourly_rate=27.01, annual_salary=56180, period="2025"),
    "carpenter": LaborRate(trade="Carpenter", region="National Average", hourly_rate=26.43, annual_salary=54960, period="2025"),
    "painter": LaborRate(trade="Painter", region="National Average", hourly_rate=22.37, annual_salary=46530, period="2025"),
    "roofer": LaborRate(trade="Roofer", region="National Average", hourly_rate=23.73, annual_salary=49360, period="2025"),
    "mason": LaborRate(trade="Mason", region="National Average", hourly_rate=28.27, annual_salary=58810, period="2025"),
    "welder": LaborRate(trade="Welder", region="National Average", hourly_rate=23.09, annual_salary=48030, period="2025"),
    "general_contractor": LaborRate(trade="General Contractor (Supervisor)", region="National Average", hourly_rate=37.14, annual_salary=77260, period="2025"),
    "sheet_metal": LaborRate(trade="Sheet Metal Worker", region="National Average", hourly_rate=28.79, annual_salary=59890, period="2025"),
    "insulation": LaborRate(trade="Insulation Worker", region="National Average", hourly_rate=24.10, annual_salary=50130, period="2025"),
    "concrete": LaborRate(trade="Concrete Finisher", region="National Average", hourly_rate=24.42, annual_salary=50800, period="2025"),
}

# Regional cost multipliers relative to national average
REGIONAL_MULTIPLIERS = {
    "san francisco": 1.45,
    "new york": 1.40,
    "los angeles": 1.25,
    "boston": 1.30,
    "seattle": 1.25,
    "chicago": 1.15,
    "denver": 1.10,
    "miami": 1.05,
    "dallas": 0.95,
    "houston": 0.95,
    "phoenix": 0.90,
    "atlanta": 0.90,
}


async def get_material_prices(
    material: Optional[str] = None,
    category: Optional[str] = None,
) -> list[MaterialPrice]:
    """Get current material prices. Filter by material name or category."""
    from . import config as cfg
    if getattr(cfg, "DEMO_MODE", False) or True:  # Always use built-in data for now
        results = list(MATERIAL_PRICES.values())

        if material:
            keyword = material.lower()
            results = [m for m in results if keyword in m.material.lower()]

        if category:
            cat = category.lower()
            category_map = {
                "lumber": ["lumber", "plywood", "osb"],
                "plumbing": ["copper", "pvc", "pipe"],
                "electrical": ["romex", "wire"],
                "concrete": ["concrete", "rebar"],
                "insulation": ["insulation"],
                "roofing": ["shingle"],
                "paint": ["paint"],
                "hvac": ["hvac", "ac unit"],
                "drywall": ["drywall"],
            }
            keywords = category_map.get(cat, [cat])
            results = [m for m in results if any(k in m.material.lower() for k in keywords)]

        return results


async def get_labor_rates(
    trade: str,
    region: Optional[str] = None,
) -> LaborRate:
    """Get labor rates for a specific trade, optionally by region.

    Uses BLS Occupational Employment and Wage Statistics.
    Falls back to curated data if BLS API is unavailable.
    """
    trade_key = _normalize_trade(trade)
    if not trade_key:
        available = ", ".join(sorted(BLS_TRADE_SERIES.keys()))
        raise ValueError(
            f"Trade '{trade}' not recognized. Available trades: {available}"
        )

    from . import config as cfg
    if getattr(cfg, "DEMO_MODE", False):
        rate = FALLBACK_LABOR_RATES.get(trade_key)
        if rate and region:
            multiplier = _get_regional_multiplier(region)
            return LaborRate(
                trade=rate.trade,
                region=region.title(),
                hourly_rate=round(rate.hourly_rate * multiplier, 2),
                annual_salary=round(rate.annual_salary * multiplier, 0) if rate.annual_salary else None,
                period=rate.period,
            )
        return rate or FALLBACK_LABOR_RATES["general_contractor"]

    # Try BLS API
    try:
        rate = await _fetch_bls_rate(trade_key, region)
        if rate:
            return rate
    except (ConnectionError, Exception):
        pass

    # Fallback to curated data
    rate = FALLBACK_LABOR_RATES.get(trade_key, FALLBACK_LABOR_RATES["general_contractor"])
    if region:
        multiplier = _get_regional_multiplier(region)
        return LaborRate(
            trade=rate.trade,
            region=region.title(),
            hourly_rate=round(rate.hourly_rate * multiplier, 2),
            annual_salary=round(rate.annual_salary * multiplier, 0) if rate.annual_salary else None,
            period=rate.period,
            source="BLS (estimated with regional adjustment)",
        )
    return rate


async def _fetch_bls_rate(trade_key: str, region: Optional[str] = None) -> Optional[LaborRate]:
    """Fetch labor rate from BLS API."""
    series_info = BLS_TRADE_SERIES.get(trade_key)
    if not series_info:
        return None

    series_id = series_info["series_national"]

    payload = {
        "seriesid": [series_id],
        "startyear": "2024",
        "endyear": "2025",
    }
    if config.BLS_API_KEY:
        payload["registrationkey"] = config.BLS_API_KEY

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(config.BLS_API_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") == "REQUEST_SUCCEEDED":
            series_data = data.get("Results", {}).get("series", [{}])[0]
            values = series_data.get("data", [])
            if values:
                latest = values[0]
                hourly = float(latest["value"])
                region_name = region.title() if region else "National Average"
                multiplier = _get_regional_multiplier(region) if region else 1.0
                adjusted_hourly = round(hourly * multiplier, 2)

                return LaborRate(
                    trade=series_info["title"],
                    region=region_name,
                    hourly_rate=adjusted_hourly,
                    annual_salary=round(adjusted_hourly * 2080, 0),
                    period=f"{latest.get('year', '2025')} {latest.get('periodName', '')}".strip(),
                    source="BLS OEWS" + (" (regional adjustment)" if region and multiplier != 1.0 else ""),
                )
    except Exception:
        return None

    return None


def estimate_project_cost(
    description: str,
    square_feet: Optional[float] = None,
    trade: Optional[str] = None,
    region: Optional[str] = None,
) -> dict:
    """Generate a rough project cost estimate based on description and parameters.

    Returns a range estimate (low-mid-high) using industry per-sq-ft costs.
    """
    multiplier = _get_regional_multiplier(region) if region else 1.0

    # Per-square-foot cost ranges by project type (national average)
    project_costs = {
        "kitchen_remodel": {"low": 75, "mid": 150, "high": 250, "label": "Kitchen Remodel"},
        "bathroom_remodel": {"low": 100, "mid": 200, "high": 350, "label": "Bathroom Remodel"},
        "addition": {"low": 100, "mid": 200, "high": 400, "label": "Room Addition"},
        "new_construction": {"low": 150, "mid": 250, "high": 500, "label": "New Construction"},
        "roof_replacement": {"low": 5, "mid": 10, "high": 20, "label": "Roof Replacement"},
        "painting_interior": {"low": 2, "mid": 4, "high": 7, "label": "Interior Painting"},
        "painting_exterior": {"low": 3, "mid": 5, "high": 10, "label": "Exterior Painting"},
        "flooring": {"low": 6, "mid": 12, "high": 25, "label": "Flooring Installation"},
        "electrical_rewire": {"low": 6, "mid": 10, "high": 18, "label": "Electrical Rewire"},
        "plumbing_repipe": {"low": 5, "mid": 10, "high": 20, "label": "Plumbing Repipe"},
        "hvac_install": {"low": 12, "mid": 20, "high": 35, "label": "HVAC Installation"},
        "deck": {"low": 15, "mid": 35, "high": 75, "label": "Deck Construction"},
        "fence": {"low": 15, "mid": 30, "high": 60, "label": "Fence Installation (per linear ft)"},
        "concrete_driveway": {"low": 8, "mid": 12, "high": 18, "label": "Concrete Driveway"},
        "landscaping": {"low": 5, "mid": 15, "high": 40, "label": "Landscaping"},
    }

    # Match project type from description
    desc_lower = description.lower()
    matched_type = None
    for key, costs in project_costs.items():
        keywords = key.replace("_", " ").split()
        if any(kw in desc_lower for kw in keywords):
            matched_type = key
            break

    if not matched_type:
        # Default: general remodel range
        matched_type = "addition"

    costs = project_costs[matched_type]
    sqft = square_feet or 1000  # Default assumption

    low = round(costs["low"] * sqft * multiplier)
    mid = round(costs["mid"] * sqft * multiplier)
    high = round(costs["high"] * sqft * multiplier)

    return {
        "project_type": costs["label"],
        "square_feet": sqft,
        "region": region.title() if region else "National Average",
        "regional_multiplier": multiplier,
        "estimate": {
            "low": f"${low:,}",
            "mid": f"${mid:,}",
            "high": f"${high:,}",
        },
        "note": (
            "This is a rough estimate based on industry averages per square foot. "
            "Actual costs vary by specific materials, labor availability, site conditions, "
            "and contractor markup. Get 3+ quotes for accurate pricing."
        ),
        "includes": "Materials + labor (typical contractor pricing)",
        "excludes": "Permits, design fees, demolition, unexpected repairs",
    }


def compare_regional_costs(trade: str, regions: Optional[list[str]] = None) -> list[dict]:
    """Compare labor and material costs across metro areas."""
    trade_key = _normalize_trade(trade)
    if not trade_key:
        available = ", ".join(sorted(BLS_TRADE_SERIES.keys()))
        raise ValueError(f"Trade '{trade}' not recognized. Available: {available}")

    base_rate = FALLBACK_LABOR_RATES.get(trade_key, FALLBACK_LABOR_RATES["general_contractor"])

    if regions:
        target_regions = [r.lower() for r in regions]
    else:
        target_regions = sorted(REGIONAL_MULTIPLIERS.keys())

    results = []
    for region in target_regions:
        multiplier = REGIONAL_MULTIPLIERS.get(region, 1.0)
        results.append({
            "region": region.title(),
            "hourly_rate": round(base_rate.hourly_rate * multiplier, 2),
            "annual_salary": round(base_rate.annual_salary * multiplier, 0),
            "cost_index": round(multiplier * 100, 1),
            "vs_national": f"{'+' if multiplier >= 1 else ''}{round((multiplier - 1) * 100, 1)}%",
        })

    results.sort(key=lambda x: x["hourly_rate"], reverse=True)
    return results


def _normalize_trade(trade: str) -> Optional[str]:
    """Normalize trade name to a key in BLS_TRADE_SERIES."""
    trade_lower = trade.lower().replace("-", "_").replace(" ", "_")

    # Direct match
    if trade_lower in BLS_TRADE_SERIES:
        return trade_lower

    # Alias matching
    aliases = {
        "electric": "electrician",
        "plumbing": "plumber",
        "pipe_fitter": "plumber",
        "pipefitter": "plumber",
        "ac": "hvac",
        "air_conditioning": "hvac",
        "heating": "hvac",
        "wood": "carpenter",
        "framing": "carpenter",
        "finish_carpenter": "carpenter",
        "paint": "painter",
        "roof": "roofer",
        "roofing": "roofer",
        "brick": "mason",
        "masonry": "mason",
        "bricklayer": "mason",
        "weld": "welder",
        "welding": "welder",
        "gc": "general_contractor",
        "general": "general_contractor",
        "supervisor": "general_contractor",
        "foreman": "general_contractor",
        "sheet_metal_worker": "sheet_metal",
        "tin_knocker": "sheet_metal",
        "insulator": "insulation",
        "concrete_finisher": "concrete",
        "cement": "concrete",
    }

    if trade_lower in aliases:
        return aliases[trade_lower]

    # Fuzzy match — check if trade name is a substring of any key
    for key in BLS_TRADE_SERIES:
        if trade_lower in key or key in trade_lower:
            return key

    return None


def _get_regional_multiplier(region: Optional[str]) -> float:
    """Get regional cost multiplier for a metro area."""
    if not region:
        return 1.0
    return REGIONAL_MULTIPLIERS.get(region.lower(), 1.0)
