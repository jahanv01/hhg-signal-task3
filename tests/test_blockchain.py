"""Blockchain tests.

hash_bundle tests are pure/offline. The ChainClient tests use read-only
(gas-free) calls against the already-deployed Amoy contract and the
record submitted during Epic 4 validation (record_id 0) -- they never
submit a new transaction, to avoid spending gas on every test run.
"""
import pytest

from src.blockchain.hasher import canonical_json, hash_bundle, hash_bundle_hex

BUNDLE = {"post_url": "https://example.com/p/1", "similarity_score": 0.9}


def test_canonical_json_is_order_independent():
    a = {"b": 1, "a": 2}
    b = {"a": 2, "b": 1}
    assert canonical_json(a) == canonical_json(b)


def test_hash_bundle_is_deterministic():
    assert hash_bundle(BUNDLE) == hash_bundle(dict(BUNDLE))


def test_hash_bundle_changes_when_data_changes():
    tampered = dict(BUNDLE, similarity_score=0.1)
    assert hash_bundle(BUNDLE) != hash_bundle(tampered)


def test_hash_bundle_hex_is_32_bytes():
    hex_hash = hash_bundle_hex(BUNDLE)
    assert hex_hash.startswith("0x")
    assert len(hex_hash) == 2 + 64  # 0x + 32 bytes as hex


def test_chain_client_reads_and_reverifies_live_record():
    """Skips gracefully if CONTRACT_ADDRESS/wallet aren't configured or
    unreachable, since this hits the real Amoy network."""
    from src.blockchain.chain_client import ChainClient, ChainClientError

    try:
        client = ChainClient()
        record = client.get_record(0)
    except (ChainClientError, Exception) as exc:
        pytest.skip(f"Live Amoy contract not reachable/configured: {exc}")

    assert client.verify_hash(0, record.data_hash) is True
    assert client.verify_hash(0, hash_bundle({"different": "data"})) is False
