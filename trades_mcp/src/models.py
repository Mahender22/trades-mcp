"""Data models for trades MCP server."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


DATA_DIR = Path(__file__).parent.parent / "data"


def _load_json(filename: str) -> dict:
    """Load a JSON data file from the data/ directory."""
    path = DATA_DIR / filename
    with open(path, "r") as f:
        data = json.load(f)
    data.pop("_metadata", None)
    return data


@dataclass
class ContractorLicense:
    license_number: str
    state: str
    name: str
    business_name: Optional[str] = None
    license_type: Optional[str] = None
    classification: Optional[str] = None
    status: Optional[str] = None
    issue_date: Optional[str] = None
    expiration_date: Optional[str] = None
    bond_amount: Optional[str] = None
    workers_comp: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class BuildingPermit:
    permit_number: str
    address: str
    permit_type: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    contractor_name: Optional[str] = None
    contractor_license: Optional[str] = None
    issue_date: Optional[str] = None
    expiration_date: Optional[str] = None
    valuation: Optional[str] = None
    inspections: list = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if v is not None}
        if not self.inspections:
            d.pop("inspections", None)
        return d


@dataclass
class MaterialPrice:
    material: str
    unit: str
    price: float
    region: Optional[str] = None
    supplier: Optional[str] = None
    last_updated: Optional[str] = None
    price_trend: Optional[str] = None  # "up", "down", "stable"

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class LaborRate:
    trade: str
    region: str
    hourly_rate: float
    annual_salary: Optional[float] = None
    employment_count: Optional[int] = None
    source: str = "BLS"
    period: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


# Supported states and their license board info
SUPPORTED_STATES = {
    "CA": {
        "name": "California",
        "board": "Contractors State License Board (CSLB)",
        "url": "https://www.cslb.ca.gov",
        "lookup_url": "https://www.cslb.ca.gov/OnlineServices/CheckLicenseII/CheckLicense.aspx",
        "license_format": "7 digits (e.g., 1234567)",
        "notes": "2026 rule changes: new continuing education requirements, updated bond amounts",
    },
    "TX": {
        "name": "Texas",
        "board": "Texas Department of Licensing and Regulation (TDLR)",
        "url": "https://www.tdlr.texas.gov",
        "lookup_url": "https://www.tdlr.texas.gov/LicenseSearch/",
        "license_format": "Varies by trade",
        "notes": "Texas does not require a general contractor license; specific trades are licensed",
    },
    "FL": {
        "name": "Florida",
        "board": "Department of Business and Professional Regulation (DBPR)",
        "url": "https://www.myfloridalicense.com",
        "lookup_url": "https://www.myfloridalicense.com/wl11.asp",
        "license_format": "License prefix + number (e.g., CGC1234567)",
        "notes": "State and county licenses; some trades require both",
    },
    "NY": {
        "name": "New York",
        "board": "Department of State (DOS) / NYC DCA",
        "url": "https://www.dos.ny.gov",
        "lookup_url": "https://appext20.dos.ny.gov/nydos/selSearchType.do",
        "license_format": "Varies by locality",
        "notes": "NYC has separate licensing from state; home improvement contractor registration required",
    },
}

# Common contractor license classifications (California focus)
LICENSE_CLASSIFICATIONS = {
    "A": "General Engineering Contractor",
    "B": "General Building Contractor",
    "C-2": "Insulation and Acoustical Contractor",
    "C-4": "Boiler, Hot Water Heating and Steam Fitting",
    "C-5": "Framing and Rough Carpentry",
    "C-6": "Cabinet, Millwork and Finish Carpentry",
    "C-7": "Low Voltage Systems",
    "C-8": "Concrete",
    "C-9": "Drywall",
    "C-10": "Electrical",
    "C-11": "Elevator",
    "C-12": "Earthwork and Paving",
    "C-13": "Fencing",
    "C-15": "Flooring and Floor Covering",
    "C-16": "Fire Protection",
    "C-17": "Glazing",
    "C-20": "Warm-Air Heating, Ventilating and Air-Conditioning (HVAC)",
    "C-21": "Building Moving/Demolition",
    "C-23": "Ornamental Metal",
    "C-27": "Landscaping",
    "C-29": "Masonry",
    "C-33": "Painting and Decorating",
    "C-34": "Pipeline",
    "C-35": "Lathing and Plastering",
    "C-36": "Plumbing",
    "C-38": "Refrigeration",
    "C-39": "Roofing",
    "C-42": "Sanitation System",
    "C-43": "Sheet Metal",
    "C-45": "Signs",
    "C-46": "Solar",
    "C-47": "General Manufactured Housing",
    "C-50": "Reinforcing Steel",
    "C-51": "Structural Steel",
    "C-53": "Swimming Pool",
    "C-54": "Ceramic and Mosaic Tile",
    "C-55": "Water Conditioning",
    "C-57": "Well Drilling",
    "C-60": "Welding",
    "C-61": "Limited Specialty",
    "HAZ": "Hazardous Substance Removal",
    "ASB": "Asbestos Certification",
}

# Insurance and bond requirements — loaded from JSON data files
INSURANCE_REQUIREMENTS = _load_json("insurance_requirements.json")
BOND_REQUIREMENTS = _load_json("bond_requirements.json")
