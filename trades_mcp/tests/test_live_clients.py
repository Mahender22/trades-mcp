"""Tests for live state license clients (mocked HTTP responses)."""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock

import httpx

from trades_mcp.src import config as cfg
from trades_mcp.src.licenses import (
    tdlr_verify_license,
    tdlr_search_by_name,
    dbpr_verify_license,
    dbpr_search_by_name,
    ny_verify_license,
    ny_search_by_name,
    verify_license,
    search_by_name,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(text="", json_data=None, status_code=200):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text
    resp.json.return_value = json_data if json_data is not None else {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}", request=MagicMock(), response=resp,
        )
    return resp


def _mock_client(responses):
    """Create a mock httpx.AsyncClient that returns a sequence of responses."""
    client = AsyncMock()
    if isinstance(responses, list):
        client.get = AsyncMock(side_effect=responses)
        client.post = AsyncMock(side_effect=responses)
    else:
        client.get = AsyncMock(return_value=responses)
        client.post = AsyncMock(return_value=responses)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


# ---------------------------------------------------------------------------
# Texas TDLR (Socrata API)
# ---------------------------------------------------------------------------

TDLR_SAMPLE_RECORD = {
    "license_type": "Electrical Contractor",
    "license_number": "21539",
    "license_subtype": "EC",
    "business_name": "GARCIA, JOSE M",
    "owner_name": "GARCIA, JOSE M",
    "business_city_state_zip": "HOUSTON TX 77001",
    "business_address_line1": "123 Main St",
    "business_telephone": "7135551234",
    "license_expiration_date_mmddccyy": "12/31/2027",
}


@pytest.mark.asyncio
async def test_tdlr_verify_license():
    mock = _mock_client(_mock_response(json_data=[TDLR_SAMPLE_RECORD]))
    with patch.object(cfg, "DEMO_MODE", False), patch("httpx.AsyncClient", return_value=mock):
        result = await tdlr_verify_license("21539")
        assert result.license_number == "21539"
        assert result.state == "TX"
        assert result.name == "GARCIA, JOSE M"
        assert result.license_type == "Electrical Contractor"
        assert result.city == "HOUSTON"
        assert result.zip_code == "77001"


@pytest.mark.asyncio
async def test_tdlr_verify_license_not_found():
    mock = _mock_client(_mock_response(json_data=[]))
    with patch.object(cfg, "DEMO_MODE", False), patch("httpx.AsyncClient", return_value=mock):
        with pytest.raises(ValueError, match="not found"):
            await tdlr_verify_license("99999999")


@pytest.mark.asyncio
async def test_tdlr_search_by_name():
    mock = _mock_client(_mock_response(json_data=[TDLR_SAMPLE_RECORD, TDLR_SAMPLE_RECORD]))
    with patch.object(cfg, "DEMO_MODE", False), patch("httpx.AsyncClient", return_value=mock):
        results = await tdlr_search_by_name("GARCIA")
        assert len(results) == 2
        assert results[0].state == "TX"


# ---------------------------------------------------------------------------
# Florida DBPR (Web scraping)
# ---------------------------------------------------------------------------

DBPR_SEARCH_PAGE_HTML = """
<html><body>
<form name="reportForm">
<input name="hSID" value="TEST_SESSION_123">
</form>
</body></html>
"""

DBPR_RESULTS_HTML = """
<html><body>
<table>
<tr><td>Name</td><td>License#</td><td>Type</td><td>Status</td><td>Expires</td></tr>
<tr>
  <td>THOMPSON, DAVID W</td>
  <td>CGC1518765</td>
  <td>Certified General Contractor</td>
  <td>Current, Active</td>
  <td>08/31/2026</td>
</tr>
</table>
</body></html>
"""


@pytest.mark.asyncio
async def test_dbpr_verify_license():
    client = AsyncMock()
    client.get = AsyncMock(return_value=_mock_response(text=DBPR_SEARCH_PAGE_HTML))
    client.post = AsyncMock(return_value=_mock_response(text=DBPR_RESULTS_HTML))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    with patch.object(cfg, "DEMO_MODE", False), patch("httpx.AsyncClient", return_value=client):
        result = await dbpr_verify_license("CGC1518765")
        assert result.license_number == "CGC1518765"
        assert result.state == "FL"
        assert "THOMPSON" in result.name


@pytest.mark.asyncio
async def test_dbpr_search_by_name():
    client = AsyncMock()
    client.get = AsyncMock(return_value=_mock_response(text=DBPR_SEARCH_PAGE_HTML))
    client.post = AsyncMock(return_value=_mock_response(text=DBPR_RESULTS_HTML))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    with patch.object(cfg, "DEMO_MODE", False), patch("httpx.AsyncClient", return_value=client):
        results = await dbpr_search_by_name("THOMPSON")
        assert len(results) >= 1
        assert results[0].state == "FL"


# ---------------------------------------------------------------------------
# New York (NYC Open Data Socrata + DOB BIS)
# ---------------------------------------------------------------------------

NYC_HIC_SAMPLE = {
    "license_nbr": "2054609-DCA",
    "license_type": "Premises",
    "lic_expir_dd": "2026-12-31T00:00:00.000",
    "license_status": "Active",
    "license_creation_date": "2020-01-15T00:00:00.000",
    "business_name": "O'BRIEN HOME IMPROVEMENTS",
    "address_building": "123",
    "address_street_name": "BROADWAY",
    "address_city": "NEW YORK",
    "address_zip": "10001",
    "contact_phone": "2125551234",
}


@pytest.mark.asyncio
async def test_nyc_hic_verify():
    mock = _mock_client(_mock_response(json_data=[NYC_HIC_SAMPLE]))
    with patch.object(cfg, "DEMO_MODE", False), patch("httpx.AsyncClient", return_value=mock):
        result = await ny_verify_license("2054609-DCA")
        assert result.license_number == "2054609-DCA"
        assert result.state == "NY"
        assert "O'BRIEN" in result.name
        assert result.license_type == "Home Improvement Contractor"
        assert result.status == "Active"
        assert result.city == "NEW YORK"


@pytest.mark.asyncio
async def test_nyc_hic_search():
    mock = _mock_client(_mock_response(json_data=[NYC_HIC_SAMPLE]))
    with patch.object(cfg, "DEMO_MODE", False), patch("httpx.AsyncClient", return_value=mock):
        results = await ny_search_by_name("O'BRIEN")
        assert len(results) >= 1
        assert results[0].state == "NY"


@pytest.mark.asyncio
async def test_ny_verify_not_found():
    # Both NYC HIC and DOB return nothing
    mock = _mock_client(_mock_response(json_data=[]))
    with patch.object(cfg, "DEMO_MODE", False), patch("httpx.AsyncClient", return_value=mock):
        with pytest.raises(ValueError, match="not found"):
            await ny_verify_license("FAKE999")


# ---------------------------------------------------------------------------
# Multi-state dispatch
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dispatch_texas():
    mock = _mock_client(_mock_response(json_data=[TDLR_SAMPLE_RECORD]))
    with patch.object(cfg, "DEMO_MODE", False), patch("httpx.AsyncClient", return_value=mock):
        result = await verify_license("TX", "21539")
        assert result.state == "TX"


@pytest.mark.asyncio
async def test_dispatch_florida():
    client = AsyncMock()
    client.get = AsyncMock(return_value=_mock_response(text=DBPR_SEARCH_PAGE_HTML))
    client.post = AsyncMock(return_value=_mock_response(text=DBPR_RESULTS_HTML))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    with patch.object(cfg, "DEMO_MODE", False), patch("httpx.AsyncClient", return_value=client):
        result = await verify_license("FL", "CGC1518765")
        assert result.state == "FL"


@pytest.mark.asyncio
async def test_dispatch_new_york():
    mock = _mock_client(_mock_response(json_data=[NYC_HIC_SAMPLE]))
    with patch.object(cfg, "DEMO_MODE", False), patch("httpx.AsyncClient", return_value=mock):
        result = await verify_license("NY", "2054609-DCA")
        assert result.state == "NY"


@pytest.mark.asyncio
async def test_dispatch_unsupported():
    with pytest.raises(ValueError, match="not yet supported"):
        await verify_license("ZZ", "123")


@pytest.mark.asyncio
async def test_search_dispatch_texas():
    mock = _mock_client(_mock_response(json_data=[TDLR_SAMPLE_RECORD]))
    with patch.object(cfg, "DEMO_MODE", False), patch("httpx.AsyncClient", return_value=mock):
        results = await search_by_name("TX", "GARCIA")
        assert len(results) >= 1
        assert results[0].state == "TX"


@pytest.mark.asyncio
async def test_search_dispatch_florida():
    client = AsyncMock()
    client.get = AsyncMock(return_value=_mock_response(text=DBPR_SEARCH_PAGE_HTML))
    client.post = AsyncMock(return_value=_mock_response(text=DBPR_RESULTS_HTML))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    with patch.object(cfg, "DEMO_MODE", False), patch("httpx.AsyncClient", return_value=client):
        results = await search_by_name("FL", "THOMPSON")
        assert len(results) >= 1


@pytest.mark.asyncio
async def test_search_dispatch_new_york():
    mock = _mock_client(_mock_response(json_data=[NYC_HIC_SAMPLE]))
    with patch.object(cfg, "DEMO_MODE", False), patch("httpx.AsyncClient", return_value=mock):
        results = await search_by_name("NY", "O'BRIEN")
        assert len(results) >= 1
