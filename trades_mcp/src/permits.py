"""Building permit search and lookup clients."""

import httpx
from typing import Optional

from . import config
from .models import BuildingPermit


async def _request(method: str, url: str, **kwargs) -> httpx.Response:
    """Generic HTTP request with standardized error handling."""
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await getattr(client, method)(url, **kwargs)
            resp.raise_for_status()
            return resp
    except httpx.TimeoutException:
        raise ConnectionError(
            f"Request to {url} timed out. The permit database may be slow. Try again shortly."
        )
    except httpx.HTTPStatusError as e:
        raise ConnectionError(
            f"HTTP {e.response.status_code} from permit database. "
            "The service may be experiencing issues."
        )
    except httpx.ConnectError:
        raise ConnectionError(
            f"Could not connect to {url}. Check your internet connection."
        )


async def search_permits(
    address: Optional[str] = None,
    contractor_name: Optional[str] = None,
    permit_type: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> list[BuildingPermit]:
    """Search building permits by address, contractor, or date range.

    Returns permit records from available public databases.
    Currently supports demo data; live integrations coming soon.
    """
    from . import config as cfg
    if getattr(cfg, "DEMO_MODE", False):
        from .demo_data import get_demo_permits
        return get_demo_permits(
            address=address,
            contractor_name=contractor_name,
            city=city,
            state=state,
        )

    # For live mode, attempt to query open permit APIs
    # Many municipalities publish permit data via Socrata/OpenData
    results = []

    if city and state:
        results = await _search_open_data_permits(
            address=address,
            contractor_name=contractor_name,
            city=city,
            state=state,
            date_from=date_from,
            date_to=date_to,
        )

    if not results:
        # Return guidance on where to look
        return [BuildingPermit(
            permit_number="N/A",
            address=address or "N/A",
            status="No results found",
            description=(
                "Permit data varies by jurisdiction. Try searching directly:\n"
                "- LA: https://www.ladbsservices2.lacity.org/OnlineServices/\n"
                "- SF: https://dbiweb02.sfgov.org/dbipts/\n"
                "- Houston: https://permittingportal.houstontx.gov/\n"
                "- NYC: https://a810-bisweb.nyc.gov/bisweb/\n"
                "- Miami-Dade: https://www.miamidade.gov/permits/"
            ),
        )]

    return results


async def _search_open_data_permits(
    address: Optional[str] = None,
    contractor_name: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> list[BuildingPermit]:
    """Search open data portals for permit information."""
    # Socrata open data endpoints for major cities
    socrata_endpoints = {
        ("los angeles", "CA"): "https://data.lacity.org/resource/yv23-pmwf.json",
        ("san francisco", "CA"): "https://data.sfgov.org/resource/i98e-djp9.json",
        ("new york", "NY"): "https://data.cityofnewyork.us/resource/ipu4-2vj7.json",
        ("chicago", "IL"): "https://data.cityofchicago.org/resource/ydr8-5enu.json",
    }

    if not city or not state:
        return []

    key = (city.lower(), state.upper())
    endpoint = socrata_endpoints.get(key)
    if not endpoint:
        return []

    params = {"$limit": 20}
    if address:
        params["$where"] = f"upper(address) like upper('%{address}%')"

    try:
        resp = await _request("get", endpoint, params=params)
        data = resp.json()
        return _parse_socrata_permits(data, state)
    except (ConnectionError, Exception):
        return []


def _parse_socrata_permits(data: list[dict], state: str) -> list[BuildingPermit]:
    """Parse Socrata open data API response into BuildingPermit objects."""
    results = []
    for record in data[:20]:
        permit = BuildingPermit(
            permit_number=record.get("permit_number", record.get("permit_nbr", record.get("job__", "N/A"))),
            address=record.get("address", record.get("street_address", record.get("house__", "N/A"))),
            permit_type=record.get("permit_type", record.get("work_type", record.get("job_type", None))),
            status=record.get("status", record.get("permit_status", record.get("job_status", None))),
            description=record.get("description", record.get("work_description", record.get("job_description", None))),
            contractor_name=record.get("contractor_name", record.get("owner_s_business_name", None)),
            issue_date=record.get("issue_date", record.get("issued_date", record.get("issuance_date", None))),
            expiration_date=record.get("expiration_date", None),
            valuation=str(record.get("valuation", record.get("initial_cost", ""))) or None,
        )
        results.append(permit)
    return results


async def get_permit_details(permit_number: str, city: Optional[str] = None, state: Optional[str] = None) -> BuildingPermit:
    """Get full details for a specific building permit."""
    from . import config as cfg
    if getattr(cfg, "DEMO_MODE", False):
        from .demo_data import get_demo_permit_detail
        return get_demo_permit_detail(permit_number)

    # Try to find the permit in open data
    if city and state:
        results = await _search_open_data_permits(address=None, city=city, state=state)
        for p in results:
            if p.permit_number == permit_number:
                return p

    return BuildingPermit(
        permit_number=permit_number,
        address="N/A",
        status="Not found",
        description=(
            f"Could not find permit {permit_number}. "
            "Try searching by address instead, or check the local building department directly."
        ),
    )
