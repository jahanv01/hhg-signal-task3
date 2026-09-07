"""End-to-end orchestration: face scan -> web search -> match verification
-> evidence bundle -> IPFS -> blockchain -> re-verification.

Used by both the CLI and the Streamlit app so the two never drift.
"""
import datetime
import hashlib
from dataclasses import dataclass, field

from src.blockchain.chain_client import ChainClient, ChainClientError
from src.blockchain.hasher import hash_bundle, hash_bundle_hex
from src.face.detector import NoFaceFoundError, detect_primary_face
from src.face.encoder import encode_face
from src.search.matcher import VerifiedMatch, best_match, verify_candidates
from src.search.serpapi_client import SearchError, filter_social_candidates, reverse_image_search
from src.storage.ipfs_client import IpfsError, pin_json


@dataclass
class StageResult:
    name: str
    status: str  # "success" | "failed"
    message: str = ""


@dataclass
class PipelineResult:
    stages: list[StageResult] = field(default_factory=list)
    success: bool = False
    evidence_bundle: dict | None = None
    data_hash_hex: str | None = None
    ipfs_cid: str | None = None
    tx_hash: str | None = None
    explorer_url: str | None = None
    record_id: int | None = None
    reverify_ok: bool | None = None
    best_match: VerifiedMatch | None = None


def _sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run_pipeline(image_path: str) -> PipelineResult:
    result = PipelineResult()

    # Stage 1: face identification
    try:
        face = detect_primary_face(image_path)
        query_embedding = encode_face(face.crop).vector
        result.stages.append(StageResult(
            "face_identification", "success",
            f"Face detected (confidence {face.confidence:.2f})",
        ))
    except NoFaceFoundError as e:
        result.stages.append(StageResult("face_identification", "failed", str(e)))
        return result

    # Stage 2: web/social search
    try:
        candidates = reverse_image_search(image_path)
        social_candidates = filter_social_candidates(candidates)
        result.stages.append(StageResult(
            "web_search", "success",
            f"{len(candidates)} visual matches found ({len(social_candidates)} on known social domains)",
        ))
    except SearchError as e:
        result.stages.append(StageResult("web_search", "failed", str(e)))
        return result

    # Stage 2b: two-layer match verification (the differentiator)
    verified = verify_candidates(query_embedding, social_candidates)
    match = best_match(verified)
    if match is None:
        result.stages.append(StageResult(
            "match_verification", "failed",
            "No candidate's face matched the query above the confidence threshold",
        ))
        return result
    result.best_match = match
    result.stages.append(StageResult(
        "match_verification", "success",
        f"Best match: {match.candidate.link} (confidence {match.confidence:.2f})",
    ))

    # Build the evidence bundle
    bundle = {
        "post_url": match.candidate.link,
        "post_source": match.candidate.source,
        "post_title": match.candidate.title,
        "face_match_confidence": round(match.confidence, 4),
        "face_match_distance": round(match.face_distance, 4) if match.face_distance is not None else None,
        "query_image_sha256": _sha256_file(image_path),
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    result.evidence_bundle = bundle
    result.data_hash_hex = hash_bundle_hex(bundle)

    # Stage 3a: pin full bundle to IPFS
    try:
        cid = pin_json(bundle, name="hhg-signal-task3-evidence")
        result.ipfs_cid = cid
        result.stages.append(StageResult("ipfs_storage", "success", f"Pinned to IPFS: {cid}"))
    except IpfsError as e:
        result.stages.append(StageResult("ipfs_storage", "failed", str(e)))
        return result

    # Stage 3b: register hash + CID on-chain
    data_hash = hash_bundle(bundle)
    try:
        client = ChainClient()
        submitted = client.register_record(data_hash, cid)
        result.tx_hash = submitted.tx_hash
        result.explorer_url = submitted.explorer_url
        result.record_id = submitted.record_id
        result.stages.append(StageResult(
            "blockchain_registration", "success",
            f"Record #{submitted.record_id} registered on Polygon Amoy",
        ))
    except ChainClientError as e:
        result.stages.append(StageResult("blockchain_registration", "failed", str(e)))
        return result

    # Stage 4: re-verification (read back on-chain, recompute locally, compare)
    reverify_ok = client.verify_hash(submitted.record_id, data_hash)
    result.reverify_ok = reverify_ok
    result.stages.append(StageResult(
        "re_verification",
        "success" if reverify_ok else "failed",
        f"Recomputed hash {'matches' if reverify_ok else 'does NOT match'} the on-chain record",
    ))

    result.success = reverify_ok
    return result
