"""Tests for data models."""

from trades_mcp.src.models import (
    ContractorLicense,
    BuildingPermit,
    MaterialPrice,
    LaborRate,
    SUPPORTED_STATES,
    LICENSE_CLASSIFICATIONS,
    INSURANCE_REQUIREMENTS,
    BOND_REQUIREMENTS,
)


def test_contractor_license_to_dict():
    lic = ContractorLicense(
        license_number="1234567",
        state="CA",
        name="Test Contractor",
        status="Active",
    )
    d = lic.to_dict()
    assert d["license_number"] == "1234567"
    assert d["state"] == "CA"
    assert d["name"] == "Test Contractor"
    assert d["status"] == "Active"
    # None fields should be excluded
    assert "business_name" not in d
    assert "phone" not in d


def test_building_permit_to_dict():
    permit = BuildingPermit(
        permit_number="BLD-001",
        address="123 Main St",
        status="Issued",
    )
    d = permit.to_dict()
    assert d["permit_number"] == "BLD-001"
    assert "inspections" not in d  # Empty list excluded


def test_building_permit_with_inspections():
    permit = BuildingPermit(
        permit_number="BLD-001",
        address="123 Main St",
        inspections=[{"type": "Foundation", "status": "Passed"}],
    )
    d = permit.to_dict()
    assert "inspections" in d
    assert len(d["inspections"]) == 1


def test_material_price_to_dict():
    price = MaterialPrice(
        material="Lumber 2x4",
        unit="per piece",
        price=3.98,
        price_trend="stable",
    )
    d = price.to_dict()
    assert d["price"] == 3.98
    assert d["price_trend"] == "stable"


def test_labor_rate_to_dict():
    rate = LaborRate(
        trade="Electrician",
        region="National Average",
        hourly_rate=29.61,
        annual_salary=61590,
    )
    d = rate.to_dict()
    assert d["hourly_rate"] == 29.61
    assert d["source"] == "BLS"


def test_supported_states_coverage():
    assert "CA" in SUPPORTED_STATES
    assert "TX" in SUPPORTED_STATES
    assert "FL" in SUPPORTED_STATES
    assert "NY" in SUPPORTED_STATES
    # Each state should have required fields
    for code, info in SUPPORTED_STATES.items():
        assert "name" in info
        assert "board" in info
        assert "lookup_url" in info


def test_license_classifications():
    assert "B" in LICENSE_CLASSIFICATIONS
    assert "General Building" in LICENSE_CLASSIFICATIONS["B"]
    assert "C-10" in LICENSE_CLASSIFICATIONS
    assert "Electrical" in LICENSE_CLASSIFICATIONS["C-10"]
    assert "C-36" in LICENSE_CLASSIFICATIONS
    assert "Plumbing" in LICENSE_CLASSIFICATIONS["C-36"]


def test_insurance_requirements_all_states():
    for state in ["CA", "TX", "FL", "NY"]:
        assert state in INSURANCE_REQUIREMENTS
        req = INSURANCE_REQUIREMENTS[state]
        assert "workers_comp" in req
        assert "general_liability" in req
        assert "bond" in req


def test_bond_requirements_all_states():
    for state in ["CA", "TX", "FL", "NY"]:
        assert state in BOND_REQUIREMENTS
        bonds = BOND_REQUIREMENTS[state]
        assert "contractor_license_bond" in bonds
        assert "bid_bond" in bonds
