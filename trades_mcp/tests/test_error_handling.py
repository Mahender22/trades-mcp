"""Tests for error handling in HTTP clients."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

import httpx

from trades_mcp.src.licenses import _request as license_request


def _make_mock_client(side_effect=None, status_code=200, json_data=None):
    """Create a mock httpx.AsyncClient for testing."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.text = ""
    mock_response.json.return_value = json_data or {}
    mock_response.raise_for_status = MagicMock()

    if status_code >= 400:
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=mock_response,
        )

    mock_client = AsyncMock()
    if side_effect:
        mock_client.get = AsyncMock(side_effect=side_effect)
        mock_client.post = AsyncMock(side_effect=side_effect)
    else:
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.post = AsyncMock(return_value=mock_response)

    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


@pytest.mark.asyncio
async def test_timeout_error():
    mock = _make_mock_client(side_effect=httpx.TimeoutException("timed out"))
    with patch("httpx.AsyncClient", return_value=mock):
        with pytest.raises(ConnectionError, match="timed out"):
            await license_request("get", "https://example.com")


@pytest.mark.asyncio
async def test_rate_limit_error():
    mock = _make_mock_client(status_code=429)
    with patch("httpx.AsyncClient", return_value=mock):
        with pytest.raises(ConnectionError, match="Rate limited"):
            await license_request("get", "https://example.com")


@pytest.mark.asyncio
async def test_connection_error():
    mock = _make_mock_client(side_effect=httpx.ConnectError("refused"))
    with patch("httpx.AsyncClient", return_value=mock):
        with pytest.raises(ConnectionError, match="Could not connect"):
            await license_request("get", "https://example.com")


@pytest.mark.asyncio
async def test_server_error():
    mock = _make_mock_client(status_code=500)
    with patch("httpx.AsyncClient", return_value=mock):
        with pytest.raises(ConnectionError, match="HTTP 500"):
            await license_request("get", "https://example.com")
