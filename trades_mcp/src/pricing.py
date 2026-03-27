"""Material pricing, BLS labor rates, and project cost estimation.

Data sources:
- Labor rates: BLS API (live) with JSON file fallback
- Material prices: JSON data file (updated monthly)
- Regional multipliers: JSON data file (updated annually)
- Project costs: JSON data file (updated annually)
- BLS series/aliases: JSON data file (stable reference)
"""

import json
from pathlib import Path
from typing import Optional

import httpx

from . import config
from .models import MaterialPrice, LaborRate


# ---------------------------------------------------------------------------
# Data loading — all reference data lives in JSON files under data/
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "data"


def _load_json(filename: str) -> dict:
    """Load a JSON data file from the data/ directory."""
    path = DATA_DIR / filename
    with open(path, "r") as f:
        data = json.load(f)
    # Strip _metadata key — it's for humans, not code
    data.pop("_metadata", None)
    return data


def _load_material_prices() -> dict[str, MaterialPrice]:
    """Load material prices from JSON into MaterialPrice objects."""
    raw = _load_json("material_prices.json")
    return {
        key: MaterialPrice(**val)
        for key, val in raw.items()
    }


def _load_labor_rates() -> dict[str, LaborRate]:
    """Load fallback labor rates from JSON into LaborRate objects."""
    raw = _load_json("labor_rates.json")
    return {
        key: LaborRate(**val)
        for key, val in raw.items()
    }


def _load_regional_multipliers() -> dict[str, float]:
    """Load regional cost multipliers from JSON."""
    return _load_json("regional_multipliers.json")


def _load_project_costs() -> dict[str, dict]:
    """Load per-sqft project cost ranges from JSON."""
    return _load_json("project_costs.json")


def _load_bls_series() -> dict:
    """Load BLS series IDs, metro area codes, and trade aliases from JSON."""
    return _load_json("bls_series.json")


# Load all data at module import — files are small, read once
MATERIAL_PRICES = _load_material_prices()
FALLBACK_LABOR_RATES = _load_labor_rates()
REGIONAL_MULTIPLIERS = _load_regional_multipliers()
PROJECT_COSTS = _load_project_costs()
_bls_data = _load_bls_series()
BLS_TRADE_SERIES = _bls_data["trades"]
BLS_METRO_AREAS = _bls_data["metro_areas"]
TRADE_ALIASES = _bls_data["trade_aliases"]


# ---------------------------------------------------------------------------
# Material prices
# ---------------------------------------------------------------------------

async def get_material_prices(
    material: Optional[str] = None,
    category: Optional[str] = None,
) -> list[MaterialPrice]:
    """Get current material prices. Filter by material name or category."""
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


# ---------------------------------------------------------------------------
# Labor rates — BLS API primary, JSON fallback
# ---------------------------------------------------------------------------

async def get_labor_rates(
    trade: str,
    region: Optional[str] = None,
) -> LaborRate:
    """Get labor rates for a specific trade, optionally by region.

    Uses BLS Occupational Employment and Wage Statistics API.
    Falls back to data/labor_rates.json if BLS API is unavailable.
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

    # Try BLS API first — live data
    try:
        rate = await _fetch_bls_rate(trade_key, region)
        if rate:
            return rate
    except (ConnectionError, Exception):
        pass

    # Fallback to data file
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
    """Fetch labor rate from BLS API — live data."""
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


# ---------------------------------------------------------------------------
# Project cost estimation
# ---------------------------------------------------------------------------

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

    # Match project type from description
    desc_lower = description.lower()
    matched_type = None
    for key, costs in PROJECT_COSTS.items():
        keywords = key.replace("_", " ").split()
        if any(kw in desc_lower for kw in keywords):
            matched_type = key
            break

    if not matched_type:
        matched_type = "addition"

    costs = PROJECT_COSTS[matched_type]
    sqft = square_feet or 1000

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_trade(trade: str) -> Optional[str]:
    """Normalize trade name to a key in BLS_TRADE_SERIES."""
    trade_lower = trade.lower().replace("-", "_").replace(" ", "_")

    if trade_lower in BLS_TRADE_SERIES:
        return trade_lower

    if trade_lower in TRADE_ALIASES:
        return TRADE_ALIASES[trade_lower]

    for key in BLS_TRADE_SERIES:
        if trade_lower in key or key in trade_lower:
            return key

    return None


def _get_regional_multiplier(region: Optional[str]) -> float:
    """Get regional cost multiplier for a metro area."""
    if not region:
        return 1.0
    return REGIONAL_MULTIPLIERS.get(region.lower(), 1.0)
