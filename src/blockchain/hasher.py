"""Canonicalize an evidence bundle and hash it for on-chain storage."""
import hashlib
import json


def canonical_json(bundle: dict) -> str:
    """Deterministic JSON serialization: sorted keys, no whitespace variance,
    so the same logical bundle always hashes the same way."""
    return json.dumps(bundle, sort_keys=True, separators=(",", ":"))


def hash_bundle(bundle: dict) -> bytes:
    """sha256 of the canonical bundle, as raw 32 bytes (ready for bytes32 on-chain)."""
    return hashlib.sha256(canonical_json(bundle).encode("utf-8")).digest()


def hash_bundle_hex(bundle: dict) -> str:
    """Same hash, as a 0x-prefixed hex string."""
    return "0x" + hash_bundle(bundle).hex()
