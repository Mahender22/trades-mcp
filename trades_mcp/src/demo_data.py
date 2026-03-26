"""Demo data for testing without hitting real APIs."""

from typing import Optional

from .models import ContractorLicense, BuildingPermit


# ---------------------------------------------------------------------------
# Demo contractor licenses
# ---------------------------------------------------------------------------
DEMO_LICENSES = {
    "CA": [
        ContractorLicense(
            license_number="1098765",
            state="CA",
            name="MARTINEZ, CARLOS J",
            business_name="Martinez & Sons General Contracting Inc",
            license_type="Contractor",
            classification="B - General Building Contractor",
            status="Active",
            issue_date="03/15/2015",
            expiration_date="03/31/2027",
            bond_amount="$25,000",
            workers_comp="State Compensation Ins Fund",
            address="1234 Maple Ave",
            city="Los Angeles",
        ),
        ContractorLicense(
            license_number="0876543",
            state="CA",
            name="JOHNSON, MICHAEL R",
            business_name="Johnson Electric Co",
            license_type="Contractor",
            classification="C-10 - Electrical",
            status="Active",
            issue_date="06/01/2018",
            expiration_date="06/30/2026",
            bond_amount="$25,000",
            workers_comp="Hartford Insurance",
            address="5678 Oak Blvd",
            city="San Francisco",
        ),
        ContractorLicense(
            license_number="0654321",
            state="CA",
            name="NGUYEN, DAVID T",
            business_name="Nguyen Plumbing & Heating",
            license_type="Contractor",
            classification="C-36 - Plumbing",
            status="Active",
            issue_date="01/10/2012",
            expiration_date="01/31/2026",
            bond_amount="$25,000",
            workers_comp="Zenith Insurance",
            address="910 Pine St",
            city="Sacramento",
        ),
        ContractorLicense(
            license_number="0543210",
            state="CA",
            name="WILLIAMS, ROBERT A",
            business_name="Williams Roofing Solutions LLC",
            license_type="Contractor",
            classification="C-39 - Roofing",
            status="Inactive",
            issue_date="09/20/2010",
            expiration_date="09/30/2024",
            bond_amount="$15,000",
            workers_comp="Expired",
            city="San Diego",
        ),
        ContractorLicense(
            license_number="1234567",
            state="CA",
            name="SMITH, SARAH K",
            business_name="Smith HVAC Services",
            license_type="Contractor",
            classification="C-20 - HVAC",
            status="Active",
            issue_date="11/05/2020",
            expiration_date="11/30/2026",
            bond_amount="$25,000",
            workers_comp="State Fund",
            city="Fresno",
        ),
    ],
    "TX": [
        ContractorLicense(
            license_number="ACR-7654321",
            state="TX",
            name="GARCIA, JOSE M",
            business_name="Garcia AC & Heating",
            license_type="Air Conditioning and Refrigeration Contractor",
            classification="ACR",
            status="Active",
            issue_date="2019-04-15",
            expiration_date="2026-04-14",
            city="Houston",
        ),
        ContractorLicense(
            license_number="ELEC-9876543",
            state="TX",
            name="BROWN, JAMES L",
            business_name="Brown Electrical Services",
            license_type="Master Electrician",
            classification="Electrical",
            status="Active",
            issue_date="2017-08-20",
            expiration_date="2026-08-19",
            city="Dallas",
        ),
    ],
    "FL": [
        ContractorLicense(
            license_number="CGC1518765",
            state="FL",
            name="THOMPSON, DAVID W",
            business_name="Thompson General Contracting",
            license_type="Certified General Contractor",
            classification="CGC",
            status="Current, Active",
            issue_date="2016-02-01",
            expiration_date="2026-08-31",
            city="Miami",
        ),
        ContractorLicense(
            license_number="CFC1432109",
            state="FL",
            name="PATEL, AMIT R",
            business_name="Patel Plumbing Inc",
            license_type="Certified Plumbing Contractor",
            classification="CFC",
            status="Current, Active",
            issue_date="2018-05-10",
            expiration_date="2026-08-31",
            city="Orlando",
        ),
    ],
    "NY": [
        ContractorLicense(
            license_number="HIC-2098765",
            state="NY",
            name="O'BRIEN, PATRICK J",
            business_name="O'Brien Home Improvements",
            license_type="Home Improvement Contractor",
            classification="HIC",
            status="Active",
            issue_date="2020-01-15",
            expiration_date="2026-01-14",
            city="New York",
        ),
    ],
}


# ---------------------------------------------------------------------------
# Demo building permits
# ---------------------------------------------------------------------------
DEMO_PERMITS = [
    BuildingPermit(
        permit_number="BLD-2026-00142",
        address="1234 Maple Ave, Los Angeles, CA 90012",
        permit_type="Building - Commercial Alteration",
        status="Issued",
        description="Tenant improvement for restaurant space, 2500 sq ft, includes new HVAC, plumbing, electrical",
        contractor_name="Martinez & Sons General Contracting Inc",
        contractor_license="1098765",
        issue_date="2026-02-15",
        expiration_date="2027-02-15",
        valuation="$450,000",
        inspections=[
            {"type": "Foundation", "date": "2026-03-01", "status": "Passed"},
            {"type": "Framing", "date": "2026-03-15", "status": "Passed"},
            {"type": "Electrical Rough", "date": "2026-03-20", "status": "Scheduled"},
        ],
    ),
    BuildingPermit(
        permit_number="BLD-2026-00098",
        address="5678 Oak Blvd, San Francisco, CA 94102",
        permit_type="Building - Residential Addition",
        status="Under Review",
        description="Second story addition to single family residence, 800 sq ft, 2 bedrooms 1 bath",
        contractor_name="Smith & Co Construction",
        contractor_license="0987654",
        issue_date="2026-01-20",
        valuation="$280,000",
    ),
    BuildingPermit(
        permit_number="ELEC-2026-00321",
        address="910 Pine St, Sacramento, CA 95814",
        permit_type="Electrical - Panel Upgrade",
        status="Final Approved",
        description="Upgrade electrical panel from 100A to 200A service, residential",
        contractor_name="Johnson Electric Co",
        contractor_license="0876543",
        issue_date="2026-01-05",
        expiration_date="2026-07-05",
        valuation="$8,500",
        inspections=[
            {"type": "Rough Electrical", "date": "2026-01-20", "status": "Passed"},
            {"type": "Final Electrical", "date": "2026-02-10", "status": "Passed"},
        ],
    ),
    BuildingPermit(
        permit_number="PLM-2026-00205",
        address="4321 Elm Dr, Houston, TX 77001",
        permit_type="Plumbing - Repipe",
        status="Issued",
        description="Whole house repipe, replace galvanized with PEX, 2400 sq ft residence",
        contractor_name="Garcia Plumbing Services",
        issue_date="2026-03-01",
        expiration_date="2026-09-01",
        valuation="$12,000",
    ),
    BuildingPermit(
        permit_number="BLD-2026-00567",
        address="7890 Beach Rd, Miami, FL 33101",
        permit_type="Building - New Construction",
        status="Approved",
        description="New single family residence, 3200 sq ft, 4 bed 3 bath, concrete block construction",
        contractor_name="Thompson General Contracting",
        contractor_license="CGC1518765",
        issue_date="2026-02-28",
        expiration_date="2027-02-28",
        valuation="$680,000",
        inspections=[
            {"type": "Foundation", "date": "2026-03-15", "status": "Passed"},
        ],
    ),
    BuildingPermit(
        permit_number="ROOF-2026-00089",
        address="2468 Summit Way, Denver, CO 80202",
        permit_type="Roofing - Reroof",
        status="Issued",
        description="Complete tear-off and reroof, architectural shingles, 2800 sq ft roof area",
        contractor_name="Mountain Top Roofing LLC",
        issue_date="2026-03-10",
        expiration_date="2026-09-10",
        valuation="$18,500",
    ),
]


def get_demo_license(state: str, license_number: str) -> ContractorLicense:
    """Get a demo license record by state and license number."""
    state = state.upper()
    licenses = DEMO_LICENSES.get(state, [])
    for lic in licenses:
        if lic.license_number == license_number:
            return lic
    # Return the first license as a fallback
    if licenses:
        return licenses[0]
    raise ValueError(f"No demo data for state {state}, license {license_number}")


def get_demo_search_results(state: str, name: str) -> list[ContractorLicense]:
    """Get demo license search results matching a name."""
    state = state.upper()
    licenses = DEMO_LICENSES.get(state, [])
    name_lower = name.lower()
    results = [
        lic for lic in licenses
        if name_lower in lic.name.lower()
        or (lic.business_name and name_lower in lic.business_name.lower())
    ]
    # If no keyword match, return all for that state
    return results if results else licenses


def get_demo_permits(
    address: Optional[str] = None,
    contractor_name: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
) -> list[BuildingPermit]:
    """Get demo permits filtered by criteria."""
    results = DEMO_PERMITS

    if address:
        addr_lower = address.lower()
        results = [p for p in results if addr_lower in p.address.lower()]

    if contractor_name:
        name_lower = contractor_name.lower()
        results = [p for p in results if p.contractor_name and name_lower in p.contractor_name.lower()]

    if city:
        city_lower = city.lower()
        results = [p for p in results if city_lower in p.address.lower()]

    if state:
        state_upper = state.upper()
        results = [p for p in results if f", {state_upper} " in p.address or p.address.endswith(f", {state_upper}")]

    return results if results else DEMO_PERMITS[:3]


def get_demo_permit_detail(permit_number: str) -> BuildingPermit:
    """Get a demo permit by permit number."""
    for p in DEMO_PERMITS:
        if p.permit_number == permit_number:
            return p
    return DEMO_PERMITS[0]
