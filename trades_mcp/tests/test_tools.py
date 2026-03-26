"""Integration tests — call tools through the server layer with demo mode."""

import pytest
from unittest.mock import patch

from trades_mcp.src import config
from trades_mcp.src.server import (
    verify_contractor_license,
    search_contractor_by_name,
    check_license_expiration,
    search_building_permits,
    get_permit_details,
    list_supported_states,
    get_material_prices,
    get_labor_rates,
    estimate_project_cost,
    compare_regional_costs,
    check_insurance_requirements,
    get_bond_requirements,
    track_compliance_deadlines,
)


@pytest.mark.asyncio
async def test_verify_contractor_license():
    with patch.object(config, "DEMO_MODE", True):
        result = await verify_contractor_license("CA", "1098765")
        assert result["status"] == "success"
        assert result["license"]["name"] == "MARTINEZ, CARLOS J"


@pytest.mark.asyncio
async def test_verify_contractor_license_invalid_state():
    result = await verify_contractor_license("ZZ", "123")
    assert result["status"] == "error"
    assert "not yet supported" in result["message"]


@pytest.mark.asyncio
async def test_search_contractor_by_name():
    with patch.object(config, "DEMO_MODE", True):
        result = await search_contractor_by_name("CA", "Martinez")
        assert result["status"] == "success"
        assert result["count"] >= 1


@pytest.mark.asyncio
async def test_check_license_expiration():
    with patch.object(config, "DEMO_MODE", True):
        result = await check_license_expiration("CA", "1098765")
        assert result["status"] == "success"
        assert "expiration" in result
        assert result["expiration"]["expiration_date"] is not None


@pytest.mark.asyncio
async def test_search_building_permits():
    with patch.object(config, "DEMO_MODE", True):
        result = await search_building_permits(city="Los Angeles")
        assert result["status"] == "success"
        assert result["count"] >= 1


@pytest.mark.asyncio
async def test_get_permit_details():
    with patch.object(config, "DEMO_MODE", True):
        result = await get_permit_details("BLD-2026-00142")
        assert result["status"] == "success"
        assert result["permit"]["permit_number"] == "BLD-2026-00142"


def test_list_supported_states():
    result = list_supported_states()
    assert result["status"] == "success"
    assert result["count"] == 4
    state_codes = [s["code"] for s in result["states"]]
    assert "CA" in state_codes
    assert "TX" in state_codes


@pytest.mark.asyncio
async def test_get_material_prices():
    with patch.object(config, "TIER", "pro"):
        result = await get_material_prices(category="lumber")
        assert result["status"] == "success"
        assert result["count"] >= 2


@pytest.mark.asyncio
async def test_get_material_prices_starter_blocked():
    with patch.object(config, "TIER", "starter"):
        result = await get_material_prices()
        assert result["status"] == "error"
        assert "Pro plan" in result["message"]


@pytest.mark.asyncio
async def test_get_labor_rates():
    with patch.object(config, "DEMO_MODE", True), patch.object(config, "TIER", "pro"):
        result = await get_labor_rates("electrician")
        assert result["status"] == "success"
        assert result["rate"]["hourly_rate"] > 0


@pytest.mark.asyncio
async def test_get_labor_rates_starter_blocked():
    with patch.object(config, "TIER", "starter"):
        result = await get_labor_rates("electrician")
        assert result["status"] == "error"


def test_estimate_project_cost():
    with patch.object(config, "TIER", "pro"):
        result = estimate_project_cost("kitchen remodel", square_feet=200)
        assert result["status"] == "success"
        assert "estimate" in result


def test_compare_regional_costs():
    with patch.object(config, "TIER", "pro"):
        result = compare_regional_costs("plumber")
        assert result["status"] == "success"
        assert result["count"] > 0


def test_check_insurance_requirements():
    with patch.object(config, "TIER", "pro"):
        result = check_insurance_requirements("CA")
        assert result["status"] == "success"
        assert "workers_comp" in result["requirements"]


def test_check_insurance_requirements_invalid():
    with patch.object(config, "TIER", "pro"):
        result = check_insurance_requirements("ZZ")
        assert result["status"] == "error"


def test_get_bond_requirements():
    with patch.object(config, "TIER", "pro"):
        result = get_bond_requirements("CA")
        assert result["status"] == "success"
        assert "contractor_license_bond" in result["bonds"]


@pytest.mark.asyncio
async def test_track_compliance_deadlines():
    with patch.object(config, "DEMO_MODE", True), patch.object(config, "TIER", "pro"):
        result = await track_compliance_deadlines("CA", "1098765")
        assert result["status"] == "success"
        assert len(result["deadlines"]) >= 1
        assert result["contractor"] == "MARTINEZ, CARLOS J"
