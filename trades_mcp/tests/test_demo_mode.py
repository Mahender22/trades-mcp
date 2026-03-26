"""Tests for demo mode — all tools should work with DEMO_MODE=True."""

import pytest
from unittest.mock import patch

from trades_mcp.src import config
from trades_mcp.src.licenses import verify_license, search_by_name
from trades_mcp.src.permits import search_permits, get_permit_details
from trades_mcp.src.pricing import get_material_prices, get_labor_rates, estimate_project_cost, compare_regional_costs


@pytest.mark.asyncio
async def test_demo_verify_license_ca():
    with patch.object(config, "DEMO_MODE", True):
        result = await verify_license("CA", "1098765")
        assert result.license_number == "1098765"
        assert result.state == "CA"
        assert result.name == "MARTINEZ, CARLOS J"
        assert result.status == "Active"


@pytest.mark.asyncio
async def test_demo_verify_license_tx():
    with patch.object(config, "DEMO_MODE", True):
        result = await verify_license("TX", "ACR-7654321")
        assert result.state == "TX"
        assert result.status == "Active"


@pytest.mark.asyncio
async def test_demo_verify_license_fl():
    with patch.object(config, "DEMO_MODE", True):
        result = await verify_license("FL", "CGC1518765")
        assert result.state == "FL"


@pytest.mark.asyncio
async def test_demo_verify_license_ny():
    with patch.object(config, "DEMO_MODE", True):
        result = await verify_license("NY", "HIC-2098765")
        assert result.state == "NY"


@pytest.mark.asyncio
async def test_demo_search_by_name():
    with patch.object(config, "DEMO_MODE", True):
        results = await search_by_name("CA", "Martinez")
        assert len(results) >= 1
        assert any("MARTINEZ" in r.name for r in results)


@pytest.mark.asyncio
async def test_demo_search_by_business_name():
    with patch.object(config, "DEMO_MODE", True):
        results = await search_by_name("CA", "Johnson Electric")
        assert len(results) >= 1


@pytest.mark.asyncio
async def test_demo_search_permits_by_city():
    with patch.object(config, "DEMO_MODE", True):
        results = await search_permits(city="Los Angeles")
        assert len(results) >= 1
        assert any("Los Angeles" in p.address for p in results)


@pytest.mark.asyncio
async def test_demo_search_permits_by_contractor():
    with patch.object(config, "DEMO_MODE", True):
        results = await search_permits(contractor_name="Martinez")
        assert len(results) >= 1


@pytest.mark.asyncio
async def test_demo_get_permit_details():
    with patch.object(config, "DEMO_MODE", True):
        result = await get_permit_details("BLD-2026-00142")
        assert result.permit_number == "BLD-2026-00142"
        assert result.status == "Issued"
        assert len(result.inspections) >= 1


@pytest.mark.asyncio
async def test_demo_material_prices_all():
    results = await get_material_prices()
    assert len(results) > 10


@pytest.mark.asyncio
async def test_demo_material_prices_by_category():
    results = await get_material_prices(category="lumber")
    assert len(results) >= 2
    assert all("lumber" in m.material.lower() or "plywood" in m.material.lower() or "osb" in m.material.lower() for m in results)


@pytest.mark.asyncio
async def test_demo_material_prices_by_name():
    results = await get_material_prices(material="copper")
    assert len(results) >= 1
    assert all("copper" in m.material.lower() for m in results)


@pytest.mark.asyncio
async def test_demo_labor_rates():
    with patch.object(config, "DEMO_MODE", True):
        rate = await get_labor_rates("electrician")
        assert rate.trade == "Electrician"
        assert rate.hourly_rate > 0
        assert rate.annual_salary > 0


@pytest.mark.asyncio
async def test_demo_labor_rates_with_region():
    with patch.object(config, "DEMO_MODE", True):
        rate = await get_labor_rates("plumber", region="san francisco")
        assert rate.region == "San Francisco"
        # SF should be higher than national average
        assert rate.hourly_rate > 30


@pytest.mark.asyncio
async def test_demo_labor_rates_alias():
    with patch.object(config, "DEMO_MODE", True):
        rate = await get_labor_rates("ac")  # alias for hvac
        assert "HVAC" in rate.trade or "Heating" in rate.trade


def test_estimate_project_cost_kitchen():
    result = estimate_project_cost("kitchen remodel", square_feet=200)
    assert result["project_type"] == "Kitchen Remodel"
    assert "$" in result["estimate"]["low"]
    assert "$" in result["estimate"]["mid"]
    assert "$" in result["estimate"]["high"]


def test_estimate_project_cost_with_region():
    result = estimate_project_cost("roof replacement", square_feet=2000, region="san francisco")
    assert result["regional_multiplier"] == 1.45
    assert result["region"] == "San Francisco"


def test_compare_regional_costs():
    results = compare_regional_costs("electrician")
    assert len(results) == len(compare_regional_costs("electrician"))
    # Should be sorted by hourly rate descending
    rates = [r["hourly_rate"] for r in results]
    assert rates == sorted(rates, reverse=True)


def test_compare_regional_costs_specific_regions():
    results = compare_regional_costs("plumber", regions=["new york", "houston"])
    assert len(results) == 2


def test_unsupported_state():
    with pytest.raises(ValueError, match="not yet supported"):
        import asyncio
        asyncio.get_event_loop().run_until_complete(verify_license("ZZ", "123"))


def test_unrecognized_trade():
    with pytest.raises(ValueError, match="not recognized"):
        compare_regional_costs("astronaut")
