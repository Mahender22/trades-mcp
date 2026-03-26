"""License verification clients for state contractor licensing boards.

Data sources:
- CA: CSLB website scraping (ASP.NET forms)
- TX: Socrata API at data.texas.gov (958K+ records, REST/JSON)
- FL: MyFloridaLicense.com web form (Classic ASP)
- NY: NYC Open Data Socrata API (home improvement) + NYC DOB BIS (electricians/plumbers/GCs)
"""

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


# ===========================================================================
# California CSLB (ASP.NET scraping)
# ===========================================================================

async def cslb_verify_license(license_number: str) -> ContractorLicense:
    """Verify a California contractor license by number via CSLB."""
    from . import config as cfg
    if getattr(cfg, "DEMO_MODE", False):
        from .demo_data import get_demo_license
        return get_demo_license("CA", license_number)

    url = f"{config.CSLB_BASE_URL}/CheckLicense.aspx"
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
    for row in rows[1:]:
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


# ===========================================================================
# Texas TDLR (Socrata REST API — data.texas.gov)
# ===========================================================================

TDLR_API_URL = "https://data.texas.gov/resource/7358-krk7.json"


async def tdlr_verify_license(license_number: str) -> ContractorLicense:
    """Verify a Texas contractor license via TDLR Socrata API."""
    from . import config as cfg
    if getattr(cfg, "DEMO_MODE", False):
        from .demo_data import get_demo_license
        return get_demo_license("TX", license_number)

    params = {
        "$where": f"license_number='{license_number}'",
        "$limit": 1,
    }
    resp = await _request("get", TDLR_API_URL, params=params)
    data = resp.json()

    if not data:
        raise ValueError(
            f"License {license_number} not found in Texas TDLR database. "
            "Verify the license number is correct."
        )

    return _parse_tdlr_record(data[0])


async def tdlr_search_by_name(
    name: str,
    city: Optional[str] = None,
    license_type: Optional[str] = None,
) -> list[ContractorLicense]:
    """Search Texas contractors by name via TDLR Socrata API."""
    from . import config as cfg
    if getattr(cfg, "DEMO_MODE", False):
        from .demo_data import get_demo_search_results
        return get_demo_search_results("TX", name)

    clauses = [f"upper(owner_name) like upper('%{name}%')"]
    if city:
        clauses.append(f"upper(business_city_state_zip) like upper('%{city}%')")
    if license_type:
        clauses.append(f"upper(license_type) like upper('%{license_type}%')")

    params = {
        "$where": " AND ".join(clauses),
        "$limit": 25,
    }
    resp = await _request("get", TDLR_API_URL, params=params)
    data = resp.json()

    return [_parse_tdlr_record(r) for r in data]


def _parse_tdlr_record(record: dict) -> ContractorLicense:
    """Parse a TDLR Socrata API record into ContractorLicense."""
    # Parse city from combined "CITY TX ZIPCODE" field
    city_state_zip = record.get("business_city_state_zip", "")
    city = None
    zip_code = None
    if city_state_zip:
        parts = city_state_zip.strip().rsplit(" ", 1)
        if len(parts) == 2 and parts[1].isdigit():
            zip_code = parts[1]
            city_parts = parts[0].rsplit(" ", 1)
            city = city_parts[0] if city_parts else parts[0]
        else:
            city = city_state_zip

    exp_date = record.get("license_expiration_date_mmddccyy", "")

    return ContractorLicense(
        license_number=record.get("license_number", ""),
        state="TX",
        name=record.get("owner_name", ""),
        business_name=record.get("business_name", None),
        license_type=record.get("license_type", None),
        classification=record.get("license_subtype", None),
        status="Active" if exp_date and exp_date > "03/26/2026" else "Check expiration",
        expiration_date=exp_date or None,
        address=record.get("business_address_line1", None),
        city=city,
        zip_code=zip_code,
        phone=record.get("business_telephone", None),
    )


# ===========================================================================
# Florida DBPR (MyFloridaLicense.com — Classic ASP form)
# ===========================================================================

DBPR_SEARCH_URL = "https://www.myfloridalicense.com/wl11.asp"


async def dbpr_verify_license(license_number: str) -> ContractorLicense:
    """Verify a Florida contractor license via DBPR website."""
    from . import config as cfg
    if getattr(cfg, "DEMO_MODE", False):
        from .demo_data import get_demo_license
        return get_demo_license("FL", license_number)

    # Step 1: GET the search page to obtain session ID
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(f"{DBPR_SEARCH_URL}?mode=0&SID=")
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        sid_field = soup.find("input", {"name": "hSID"})
        sid = sid_field["value"] if sid_field else ""

        # Step 2: POST search by license number
        form_data = {
            "hSearchType": "LicNbr",
            "hBoardType": "",
            "hSID": sid,
            "hDDChange": "",
            "hPageAction": "",
            "LicNbr": license_number,
            "SearchType[]": "1",
        }

        resp = await client.post(
            f"{DBPR_SEARCH_URL}?mode=2&SID={sid}",
            data=form_data,
        )
        resp.raise_for_status()

    return _parse_dbpr_results_page(resp.text, license_number)


async def dbpr_search_by_name(
    name: str,
    city: Optional[str] = None,
) -> list[ContractorLicense]:
    """Search Florida contractors by name via DBPR website."""
    from . import config as cfg
    if getattr(cfg, "DEMO_MODE", False):
        from .demo_data import get_demo_search_results
        return get_demo_search_results("FL", name)

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(f"{DBPR_SEARCH_URL}?mode=0&SID=")
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        sid_field = soup.find("input", {"name": "hSID"})
        sid = sid_field["value"] if sid_field else ""

        # Split name into parts for last/first or org search
        name_parts = name.strip().split(" ", 1)
        form_data = {
            "hSearchType": "Name",
            "hBoardType": "",
            "hSID": sid,
            "hDDChange": "",
            "hPageAction": "",
            "LastName": name_parts[0],
            "FirstName": name_parts[1] if len(name_parts) > 1 else "",
            "SearchType[]": "0",
        }
        if city:
            form_data["City"] = city

        resp = await client.post(
            f"{DBPR_SEARCH_URL}?mode=2&SID={sid}",
            data=form_data,
        )
        resp.raise_for_status()

    return _parse_dbpr_search_results(resp.text)


def _parse_dbpr_results_page(html: str, license_number: str) -> ContractorLicense:
    """Parse DBPR license detail or results page."""
    soup = BeautifulSoup(html, "html.parser")

    # Look for results table
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            cell_texts = [c.get_text(strip=True) for c in cells]
            # Look for the license number in any cell
            for i, text in enumerate(cell_texts):
                if license_number.upper() in text.upper():
                    return _extract_dbpr_license_from_row(cell_texts, license_number)

    # Try parsing detail page format (key-value pairs)
    license = _parse_dbpr_detail_page(soup, license_number)
    if license:
        return license

    raise ValueError(
        f"License {license_number} not found in Florida DBPR. "
        "Verify the license number is correct (e.g., CGC1234567, CFC1234567)."
    )


def _extract_dbpr_license_from_row(cells: list[str], license_number: str) -> ContractorLicense:
    """Extract license info from a DBPR results table row."""
    # Typical DBPR results columns: Name, License#, Type, Status, Expiry, County
    name = cells[0] if len(cells) > 0 else ""
    lic_type = cells[2] if len(cells) > 2 else None
    status = cells[3] if len(cells) > 3 else None
    expiration = cells[4] if len(cells) > 4 else None

    return ContractorLicense(
        license_number=license_number,
        state="FL",
        name=name,
        license_type=lic_type,
        status=status,
        expiration_date=expiration,
    )


def _parse_dbpr_detail_page(soup: BeautifulSoup, license_number: str) -> Optional[ContractorLicense]:
    """Try to parse DBPR detail page with label/value pairs."""
    text = soup.get_text()
    if "no records" in text.lower() or "no results" in text.lower():
        return None

    # Extract from bolded labels or table structure
    fields = {}
    for b_tag in soup.find_all("b"):
        label = b_tag.get_text(strip=True).rstrip(":")
        next_text = b_tag.next_sibling
        if next_text:
            value = next_text.strip() if isinstance(next_text, str) else next_text.get_text(strip=True)
            if value:
                fields[label.lower()] = value

    if fields:
        return ContractorLicense(
            license_number=license_number,
            state="FL",
            name=fields.get("name", fields.get("licensee name", "")),
            business_name=fields.get("dba", fields.get("doing business as", None)),
            license_type=fields.get("license type", fields.get("rank", None)),
            status=fields.get("status", fields.get("primary status", None)),
            expiration_date=fields.get("expires", fields.get("expiration date", None)),
            city=fields.get("city", None),
        )
    return None


def _parse_dbpr_search_results(html: str) -> list[ContractorLicense]:
    """Parse DBPR name search results."""
    soup = BeautifulSoup(html, "html.parser")
    results = []

    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:]:  # Skip header
            cells = row.find_all("td")
            if len(cells) >= 3:
                cell_texts = [c.get_text(strip=True) for c in cells]
                # Skip empty rows or header-like rows
                if not cell_texts[0] or cell_texts[0].lower() in ("name", "licensee"):
                    continue
                results.append(ContractorLicense(
                    license_number=cell_texts[1] if len(cell_texts) > 1 else "",
                    state="FL",
                    name=cell_texts[0],
                    license_type=cell_texts[2] if len(cell_texts) > 2 else None,
                    status=cell_texts[3] if len(cell_texts) > 3 else None,
                    expiration_date=cell_texts[4] if len(cell_texts) > 4 else None,
                ))

    return results


# ===========================================================================
# New York — NYC Open Data (Socrata) + NYC DOB BIS
# ===========================================================================

NYC_HIC_API_URL = "https://data.cityofnewyork.us/resource/acd4-wkax.json"
NYC_DOB_SEARCH_URL = "https://a810-bisweb.nyc.gov/bisweb/LicenseQueryServlet"


async def ny_verify_license(license_number: str) -> ContractorLicense:
    """Verify a New York contractor license.

    Checks NYC Open Data for home improvement contractors,
    then NYC DOB BIS for electricians/plumbers/GCs.
    """
    from . import config as cfg
    if getattr(cfg, "DEMO_MODE", False):
        from .demo_data import get_demo_license
        return get_demo_license("NY", license_number)

    # Try NYC home improvement (Socrata) first
    result = await _nyc_hic_verify(license_number)
    if result:
        return result

    # Try NYC DOB BIS
    result = await _nyc_dob_verify(license_number)
    if result:
        return result

    raise ValueError(
        f"License {license_number} not found in NYC databases. "
        "Note: NY licensing is decentralized — check your specific county/municipality "
        "if the contractor works outside NYC."
    )


async def ny_search_by_name(
    name: str,
    city: Optional[str] = None,
) -> list[ContractorLicense]:
    """Search New York contractors by name."""
    from . import config as cfg
    if getattr(cfg, "DEMO_MODE", False):
        from .demo_data import get_demo_search_results
        return get_demo_search_results("NY", name)

    results = []

    # Search NYC home improvement (Socrata)
    hic_results = await _nyc_hic_search(name)
    results.extend(hic_results)

    # Search NYC DOB BIS
    dob_results = await _nyc_dob_search(name)
    results.extend(dob_results)

    return results


async def _nyc_hic_verify(license_number: str) -> Optional[ContractorLicense]:
    """Check NYC Open Data for home improvement contractor license."""
    # Try with and without -DCA suffix
    search_num = license_number.replace("-DCA", "").strip()
    params = {
        "$where": f"license_nbr like '%{search_num}%'",
        "$limit": 1,
    }
    try:
        resp = await _request("get", NYC_HIC_API_URL, params=params)
        data = resp.json()
        if data:
            return _parse_nyc_hic_record(data[0])
    except (ConnectionError, Exception):
        pass
    return None


async def _nyc_hic_search(name: str) -> list[ContractorLicense]:
    """Search NYC Open Data for home improvement contractors by name."""
    params = {
        "$where": f"upper(business_name) like upper('%{name}%')",
        "$limit": 25,
    }
    try:
        resp = await _request("get", NYC_HIC_API_URL, params=params)
        data = resp.json()
        return [_parse_nyc_hic_record(r) for r in data]
    except (ConnectionError, Exception):
        return []


def _parse_nyc_hic_record(record: dict) -> ContractorLicense:
    """Parse NYC Open Data home improvement contractor record."""
    address_parts = [
        record.get("address_building", ""),
        record.get("address_street_name", ""),
    ]
    address = " ".join(p for p in address_parts if p).strip() or None

    return ContractorLicense(
        license_number=record.get("license_nbr", ""),
        state="NY",
        name=record.get("business_name", ""),
        license_type="Home Improvement Contractor",
        classification="HIC",
        status=record.get("license_status", ""),
        issue_date=record.get("license_creation_date", "")[:10] if record.get("license_creation_date") else None,
        expiration_date=record.get("lic_expir_dd", "")[:10] if record.get("lic_expir_dd") else None,
        address=address,
        city=record.get("address_city", None),
        zip_code=record.get("address_zip", None),
        phone=record.get("contact_phone", None),
    )


async def _nyc_dob_verify(license_number: str) -> Optional[ContractorLicense]:
    """Check NYC DOB BIS for license by number."""
    params = {
        "licenseno": license_number,
        "vlession": "N",
    }
    try:
        resp = await _request("get", NYC_DOB_SEARCH_URL, params=params)
        return _parse_dob_results(resp.text, single=True)
    except (ConnectionError, Exception):
        return None


async def _nyc_dob_search(name: str) -> list[ContractorLicense]:
    """Search NYC DOB BIS for contractors by name."""
    # DOB search uses last name
    name_parts = name.strip().split(" ", 1)
    params = {
        "vlast": name_parts[0],
        "vlession": "N",
    }
    try:
        resp = await _request("get", NYC_DOB_SEARCH_URL, params=params)
        results = _parse_dob_search_results(resp.text)
        return results
    except (ConnectionError, Exception):
        return []


def _parse_dob_results(html: str, single: bool = False) -> Optional[ContractorLicense]:
    """Parse NYC DOB BIS license detail page."""
    soup = BeautifulSoup(html, "html.parser")

    # DOB uses tables for layout — find license info in table cells
    tables = soup.find_all("table")
    fields = {}

    for table in tables:
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            for i in range(len(cells) - 1):
                label = cells[i].get_text(strip=True).rstrip(":").lower()
                value = cells[i + 1].get_text(strip=True)
                if label and value and len(label) < 40:
                    fields[label] = value

    if not fields:
        return None

    return ContractorLicense(
        license_number=fields.get("license #", fields.get("license number", fields.get("lic no", ""))),
        state="NY",
        name=fields.get("name", fields.get("licensee", "")),
        business_name=fields.get("business name", fields.get("bus. name", None)),
        license_type=fields.get("license type", fields.get("type", None)),
        status=fields.get("status", None),
        expiration_date=fields.get("expiration date", fields.get("expires", None)),
        address=fields.get("address", None),
    )


def _parse_dob_search_results(html: str) -> list[ContractorLicense]:
    """Parse NYC DOB BIS search results page."""
    soup = BeautifulSoup(html, "html.parser")
    results = []

    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        # Check if this looks like a results table
        header = rows[0].get_text(strip=True).lower()
        if "license" not in header and "name" not in header:
            continue

        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) >= 3:
                cell_texts = [c.get_text(strip=True) for c in cells]
                if not cell_texts[0]:
                    continue
                results.append(ContractorLicense(
                    license_number=cell_texts[0],
                    state="NY",
                    name=cell_texts[1] if len(cell_texts) > 1 else "",
                    license_type=cell_texts[2] if len(cell_texts) > 2 else None,
                    status=cell_texts[3] if len(cell_texts) > 3 else None,
                    expiration_date=cell_texts[4] if len(cell_texts) > 4 else None,
                ))

    return results


# ===========================================================================
# Multi-state dispatch
# ===========================================================================

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
    elif state == "TX":
        return await tdlr_verify_license(license_number)
    elif state == "FL":
        return await dbpr_verify_license(license_number)
    elif state == "NY":
        return await ny_verify_license(license_number)

    raise ValueError(f"No client implemented for state {state}")


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
    elif state == "TX":
        return await tdlr_search_by_name(name, city=city, license_type=classification)
    elif state == "FL":
        return await dbpr_search_by_name(name, city=city)
    elif state == "NY":
        return await ny_search_by_name(name, city=city)

    raise ValueError(f"No client implemented for state {state}")
