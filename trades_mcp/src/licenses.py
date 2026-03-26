"""License verification clients for state contractor licensing boards."""

import httpx
from bs4 import BeautifulSoup
from typing import Optional

from . import config
from .models import ContractorLicense, SUPPORTED_STATES


async def _request(method: str, url: str, **kwargs) -> httpx.Response:
    """Generic HTTP request with standardized error handling."""
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await getattr(client, method)(url, **kwargs)
            resp.raise_for_status()
            return resp
    except httpx.TimeoutException:
        raise ConnectionError(
            f"Request to {url} timed out after 30s. "
            "The state licensing board website may be slow or down. Try again shortly."
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise ConnectionError(
                "Rate limited by the licensing board website. Wait a minute and try again."
            )
        raise ConnectionError(
            f"HTTP {e.response.status_code} from {url}. "
            "The licensing board website may be experiencing issues."
        )
    except httpx.ConnectError:
        raise ConnectionError(
            f"Could not connect to {url}. Check your internet connection."
        )


# ---------------------------------------------------------------------------
# California CSLB
# ---------------------------------------------------------------------------

async def cslb_verify_license(license_number: str) -> ContractorLicense:
    """Verify a California contractor license by number via CSLB."""
    from . import config as cfg
    if getattr(cfg, "DEMO_MODE", False):
        from .demo_data import get_demo_license
        return get_demo_license("CA", license_number)

    url = f"{config.CSLB_BASE_URL}/CheckLicense.aspx"
    # First GET to obtain ViewState for ASP.NET form
    resp = await _request("get", url)
    soup = BeautifulSoup(resp.text, "html.parser")

    viewstate = soup.find("input", {"name": "__VIEWSTATE"})
    validation = soup.find("input", {"name": "__EVENTVALIDATION"})
    generator = soup.find("input", {"name": "__VIEWSTATEGENERATOR"})

    form_data = {
        "__VIEWSTATE": viewstate["value"] if viewstate else "",
        "__EVENTVALIDATION": validation["value"] if validation else "",
        "__VIEWSTATEGENERATOR": generator["value"] if generator else "",
        "ctl00$MainContent$txtLicNum": license_number,
        "ctl00$MainContent$btnSearch": "Search",
    }

    resp = await _request("post", url, data=form_data)
    return _parse_cslb_license_page(resp.text, license_number)


def _parse_cslb_license_page(html: str, license_number: str) -> ContractorLicense:
    """Parse CSLB license detail page HTML."""
    soup = BeautifulSoup(html, "html.parser")

    def _text(element_id: str) -> Optional[str]:
        el = soup.find(id=element_id)
        if el:
            text = el.get_text(strip=True)
            return text if text else None
        return None

    # CSLB uses span IDs for license detail fields
    name = _text("MainContent_txtLicName") or _text("MainContent_lblName")
    business = _text("MainContent_txtBusName") or _text("MainContent_lblBusinessName")
    status = _text("MainContent_txtStatus") or _text("MainContent_lblStatus")
    classification = _text("MainContent_txtClass") or _text("MainContent_lblClassification")
    expiration = _text("MainContent_txtExpDt") or _text("MainContent_lblExpireDate")
    issue_date = _text("MainContent_txtIssDt") or _text("MainContent_lblIssueDate")
    workers_comp = _text("MainContent_txtWComp") or _text("MainContent_lblWorkersComp")
    bond = _text("MainContent_txtBond") or _text("MainContent_lblBond")
    address = _text("MainContent_txtAddr") or _text("MainContent_lblAddress")
    city = _text("MainContent_txtCity") or _text("MainContent_lblCity")

    if not name and not status:
        # Try alternate page layout — results table
        table = soup.find("table", {"id": "MainContent_gvResults"})
        if table:
            rows = table.find_all("tr")
            if len(rows) > 1:
                cells = rows[1].find_all("td")
                if len(cells) >= 4:
                    return ContractorLicense(
                        license_number=license_number,
                        state="CA",
                        name=cells[1].get_text(strip=True),
                        status=cells[3].get_text(strip=True),
                        classification=cells[2].get_text(strip=True) if len(cells) > 2 else None,
                    )
        raise ValueError(
            f"License {license_number} not found on CSLB. "
            "Verify the license number is correct (should be 7 digits)."
        )

    return ContractorLicense(
        license_number=license_number,
        state="CA",
        name=name or "Unknown",
        business_name=business,
        license_type="Contractor",
        classification=classification,
        status=status,
        issue_date=issue_date,
        expiration_date=expiration,
        bond_amount=bond,
        workers_comp=workers_comp,
        address=address,
        city=city,
    )


async def cslb_search_by_name(
    name: str,
    classification: Optional[str] = None,
    city: Optional[str] = None,
    county: Optional[str] = None,
) -> list[ContractorLicense]:
    """Search California contractors by name."""
    from . import config as cfg
    if getattr(cfg, "DEMO_MODE", False):
        from .demo_data import get_demo_search_results
        return get_demo_search_results("CA", name)

    url = f"{config.CSLB_BASE_URL}/NameSearch.aspx"
    resp = await _request("get", url)
    soup = BeautifulSoup(resp.text, "html.parser")

    viewstate = soup.find("input", {"name": "__VIEWSTATE"})
    validation = soup.find("input", {"name": "__EVENTVALIDATION"})
    generator = soup.find("input", {"name": "__VIEWSTATEGENERATOR"})

    form_data = {
        "__VIEWSTATE": viewstate["value"] if viewstate else "",
        "__EVENTVALIDATION": validation["value"] if validation else "",
        "__VIEWSTATEGENERATOR": generator["value"] if generator else "",
        "ctl00$MainContent$txtName": name,
        "ctl00$MainContent$btnSearch": "Search",
    }
    if city:
        form_data["ctl00$MainContent$txtCity"] = city
    if county:
        form_data["ctl00$MainContent$txtCounty"] = county

    resp = await _request("post", url, data=form_data)
    return _parse_cslb_search_results(resp.text)


def _parse_cslb_search_results(html: str) -> list[ContractorLicense]:
    """Parse CSLB name search results table."""
    soup = BeautifulSoup(html, "html.parser")
    results = []

    table = soup.find("table", {"id": "MainContent_gvResults"})
    if not table:
        return results

    rows = table.find_all("tr")
    for row in rows[1:]:  # Skip header
        cells = row.find_all("td")
        if len(cells) >= 4:
            results.append(ContractorLicense(
                license_number=cells[0].get_text(strip=True),
                state="CA",
                name=cells[1].get_text(strip=True),
                classification=cells[2].get_text(strip=True) if len(cells) > 2 else None,
                status=cells[3].get_text(strip=True) if len(cells) > 3 else None,
                city=cells[4].get_text(strip=True) if len(cells) > 4 else None,
            ))

    return results


# ---------------------------------------------------------------------------
# Multi-state dispatch
# ---------------------------------------------------------------------------

async def verify_license(state: str, license_number: str) -> ContractorLicense:
    """Verify a contractor license in any supported state."""
    state = state.upper()
    if state not in SUPPORTED_STATES:
        raise ValueError(
            f"State '{state}' not yet supported. "
            f"Supported states: {', '.join(SUPPORTED_STATES.keys())}"
        )

    if state == "CA":
        return await cslb_verify_license(license_number)

    # TX, FL, NY — return structured placeholder with lookup guidance
    from . import config as cfg
    if getattr(cfg, "DEMO_MODE", False):
        from .demo_data import get_demo_license
        return get_demo_license(state, license_number)

    info = SUPPORTED_STATES[state]
    return ContractorLicense(
        license_number=license_number,
        state=state,
        name="[Manual lookup required]",
        status="Check the licensing board directly",
        license_type=f"Look up at: {info['lookup_url']}",
    )


async def search_by_name(
    state: str,
    name: str,
    classification: Optional[str] = None,
    city: Optional[str] = None,
) -> list[ContractorLicense]:
    """Search contractors by name in any supported state."""
    state = state.upper()
    if state not in SUPPORTED_STATES:
        raise ValueError(
            f"State '{state}' not yet supported. "
            f"Supported states: {', '.join(SUPPORTED_STATES.keys())}"
        )

    if state == "CA":
        return await cslb_search_by_name(name, classification=classification, city=city)

    from . import config as cfg
    if getattr(cfg, "DEMO_MODE", False):
        from .demo_data import get_demo_search_results
        return get_demo_search_results(state, name)

    info = SUPPORTED_STATES[state]
    return [ContractorLicense(
        license_number="N/A",
        state=state,
        name=f"Search for '{name}' at: {info['lookup_url']}",
        status="Direct web lookup required",
    )]
