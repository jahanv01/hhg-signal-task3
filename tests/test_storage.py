import pytest
import requests

from src.storage.ipfs_client import gateway_url, pin_json


def test_pin_json_and_fetch_back_roundtrip():
    """Hits the live Pinata API -- a real integration check, not mocked,
    since IPFS pinning is cheap (tiny JSON, free tier) unlike SerpApi calls."""
    bundle = {"test": "hhg-signal-task3 test_storage", "value": 1}
    try:
        cid = pin_json(bundle, name="pytest-roundtrip")
    except Exception as exc:
        pytest.skip(f"Pinata not reachable/configured: {exc}")

    response = requests.get(gateway_url(cid), timeout=15)
    assert response.status_code == 200
    assert response.json() == bundle


def test_gateway_url_format():
    assert gateway_url("abc123") == "https://gateway.pinata.cloud/ipfs/abc123"
