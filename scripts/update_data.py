"""Update local data files with latest pricing and labor rate data.

Run manually or schedule via cron/Task Scheduler:
    python scripts/update_data.py
    python scripts/update_data.py --only labor
    python scripts/update_data.py --only materials
    python scripts/update_data.py --only all

Data sources:
    - Labor rates: BLS Occupational Employment and Wage Statistics API
    - Material prices: (manual update — no free public API available)
    - Regional multipliers: Derived from BLS metro area data
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import httpx

DATA_DIR = Path(__file__).parent.parent / "trades_mcp" / "data"

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data"


def load_json(filename: str) -> dict:
    path = DATA_DIR / filename
    with open(path, "r") as f:
        return json.load(f)


def save_json(filename: str, data: dict):
    path = DATA_DIR / filename
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Saved {path}")


# ---------------------------------------------------------------------------
# Labor rates — fetch from BLS API
# ---------------------------------------------------------------------------

async def update_labor_rates(bls_api_key: str = ""):
    """Fetch latest labor rates from BLS OEWS API."""
    print("\n[Labor Rates] Fetching from BLS API...")

    bls_series = load_json("bls_series.json")
    trades = bls_series["trades"]
    current_rates = load_json("labor_rates.json")
    metadata = current_rates.pop("_metadata", {})

    current_year = datetime.now().year
    series_ids = [info["series_national"] for info in trades.values()]

    # BLS API accepts max 50 series per request
    payload = {
        "seriesid": series_ids,
        "startyear": str(current_year - 2),
        "endyear": str(current_year),
    }
    if bls_api_key:
        payload["registrationkey"] = bls_api_key

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(BLS_API_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        print(f"  ERROR: BLS API request failed: {e}")
        return False

    if data.get("status") != "REQUEST_SUCCEEDED":
        print(f"  ERROR: BLS API returned status: {data.get('status')}")
        print(f"  Message: {data.get('message', 'Unknown error')}")
        return False

    # Map series IDs back to trade keys
    series_to_trade = {}
    for trade_key, info in trades.items():
        series_to_trade[info["series_national"]] = (trade_key, info["title"])

    updated_count = 0
    for series_result in data.get("Results", {}).get("series", []):
        series_id = series_result.get("seriesID", "")
        if series_id not in series_to_trade:
            continue

        trade_key, trade_title = series_to_trade[series_id]
        values = series_result.get("data", [])
        if not values:
            continue

        latest = values[0]
        hourly_rate = float(latest["value"])
        period = f"{latest.get('year', '')} {latest.get('periodName', '')}".strip()

        current_rates[trade_key] = {
            "trade": trade_title,
            "region": "National Average",
            "hourly_rate": hourly_rate,
            "annual_salary": round(hourly_rate * 2080),
            "period": period,
        }
        updated_count += 1
        print(f"  {trade_title}: ${hourly_rate:.2f}/hr ({period})")

    today = datetime.now().strftime("%Y-%m-%d")
    metadata["last_updated"] = today
    metadata["source"] = f"Bureau of Labor Statistics, OEWS (fetched {today})"
    current_rates["_metadata"] = metadata

    save_json("labor_rates.json", current_rates)
    print(f"  Updated {updated_count}/{len(trades)} trades")
    return True


# ---------------------------------------------------------------------------
# Regional multipliers — derive from BLS metro area data
# ---------------------------------------------------------------------------

async def update_regional_multipliers(bls_api_key: str = ""):
    """Update regional multipliers by comparing metro area rates to national average."""
    print("\n[Regional Multipliers] Fetching metro area data from BLS...")

    bls_series = load_json("bls_series.json")
    metro_areas = bls_series["metro_areas"]

    # Use general contractor supervisor (47-1011) as the baseline trade
    # National series + metro series
    base_occ = "047101103"  # SOC 47-1011, data type 03 (mean hourly)
    national_series = f"OEUN000000000000{base_occ}"
    metro_series = {}
    for metro_name, area_code in metro_areas.items():
        series_id = f"OEUM{area_code}000000{base_occ}"
        metro_series[series_id] = metro_name

    all_series = [national_series] + list(metro_series.keys())

    current_year = datetime.now().year
    payload = {
        "seriesid": all_series,
        "startyear": str(current_year - 2),
        "endyear": str(current_year),
    }
    if bls_api_key:
        payload["registrationkey"] = bls_api_key

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(BLS_API_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        print(f"  ERROR: BLS API request failed: {e}")
        return False

    if data.get("status") != "REQUEST_SUCCEEDED":
        print(f"  ERROR: BLS API returned status: {data.get('status')}")
        return False

    national_rate = None
    metro_rates = {}

    for series_result in data.get("Results", {}).get("series", []):
        series_id = series_result.get("seriesID", "")
        values = series_result.get("data", [])
        if not values:
            continue

        rate = float(values[0]["value"])

        if series_id == national_series:
            national_rate = rate
        elif series_id in metro_series:
            metro_rates[metro_series[series_id]] = rate

    if not national_rate:
        print("  ERROR: Could not fetch national average rate")
        return False

    print(f"  National average: ${national_rate:.2f}/hr")

    multipliers = load_json("regional_multipliers.json")
    metadata_backup = {"_metadata": {
        "description": "Regional cost multipliers relative to national average",
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "source": f"Derived from BLS OEWS metro area wage data (fetched {datetime.now().strftime('%Y-%m-%d')})",
        "update_frequency": "annually",
    }}

    updated_count = 0
    for metro_name, metro_rate in metro_rates.items():
        multiplier = round(metro_rate / national_rate, 2)
        multipliers[metro_name] = multiplier
        updated_count += 1
        sign = "+" if multiplier >= 1 else ""
        print(f"  {metro_name.title()}: {multiplier}x ({sign}{round((multiplier - 1) * 100, 1)}%)")

    # Re-add metadata
    final = {"_metadata": metadata_backup["_metadata"]}
    final.update({k: v for k, v in multipliers.items() if k != "_metadata"})

    save_json("regional_multipliers.json", final)
    print(f"  Updated {updated_count} metro areas")
    return True


# ---------------------------------------------------------------------------
# Material prices — guided manual update
# ---------------------------------------------------------------------------

def update_material_prices_interactive():
    """Interactive prompt to update material prices."""
    print("\n[Material Prices] No free public API available for construction materials.")
    print("  Opening current prices for manual review...\n")

    prices = load_json("material_prices.json")

    print(f"  {'Material':<45} {'Price':>10}  {'Trend':>8}  {'Last Updated':>14}")
    print(f"  {'-' * 45} {'-' * 10}  {'-' * 8}  {'-' * 14}")

    for key, val in prices.items():
        if key == "_metadata" or not isinstance(val, dict) or "material" not in val:
            continue
        trend_icon = {"up": "^", "down": "v", "stable": "-"}.get(val.get("price_trend", ""), "")
        print(f"  {val['material']:<45} ${val['price']:>8.2f}  {trend_icon:>8}  {val.get('last_updated', 'N/A'):>14}")

    print(f"\n  To update prices, edit: {DATA_DIR / 'material_prices.json'}")
    print("  Suggested sources:")
    print("    - homedepot.com (check weekly ads)")
    print("    - lowes.com")
    print("    - Random Lengths (lumber futures)")
    print("    - Copper prices: kitco.com/charts/copper")
    print("    - ENR Construction Cost Index")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Update TradesMCP data files with latest pricing and labor data"
    )
    parser.add_argument(
        "--only",
        choices=["labor", "materials", "multipliers", "all"],
        default="all",
        help="Which data to update (default: all)",
    )
    parser.add_argument(
        "--bls-key",
        default="",
        help="BLS API key for higher rate limits (optional)",
    )
    args = parser.parse_args()

    import os
    bls_key = args.bls_key or os.environ.get("BLS_API_KEY", "")

    print(f"TradesMCP Data Updater — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Data directory: {DATA_DIR}")

    if args.only in ("labor", "all"):
        asyncio.run(update_labor_rates(bls_key))

    if args.only in ("multipliers", "all"):
        asyncio.run(update_regional_multipliers(bls_key))

    if args.only in ("materials", "all"):
        update_material_prices_interactive()

    print("\nDone.")


if __name__ == "__main__":
    main()
