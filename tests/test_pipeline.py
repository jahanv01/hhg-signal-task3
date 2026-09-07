"""Pipeline orchestration tests, using mocks for the network/chain calls.

The real end-to-end integration (live SerpApi + Pinata + Amoy) was
validated manually -- see the Epic 6 commit message for a full run
(record #1, https://amoy.polygonscan.com). These tests instead verify
the orchestration logic itself: stage ordering and correct short-circuit
behavior on failure, without spending API quota or gas on every run.
"""
from unittest.mock import MagicMock, patch

from src import pipeline
from src.face.detector import NoFaceFoundError
from src.search.matcher import VerifiedMatch
from src.search.serpapi_client import SearchCandidate


def test_pipeline_stops_early_when_no_face_found():
    with patch.object(pipeline, "detect_primary_face", side_effect=NoFaceFoundError("no face")):
        result = pipeline.run_pipeline("irrelevant.jpg")

    assert result.success is False
    assert len(result.stages) == 1
    assert result.stages[0].name == "face_identification"
    assert result.stages[0].status == "failed"


def test_pipeline_stops_early_when_no_genuine_match():
    fake_face = MagicMock(crop="crop", confidence=0.9)
    fake_embedding = MagicMock(vector=[0.1, 0.2])
    candidate = SearchCandidate(title="t", link="https://x.com/p", source="x.com", thumbnail="t", position=0)

    with patch.object(pipeline, "detect_primary_face", return_value=fake_face), \
         patch.object(pipeline, "encode_face", return_value=fake_embedding), \
         patch.object(pipeline, "reverse_image_search", return_value=[candidate]), \
         patch.object(pipeline, "filter_social_candidates", return_value=[candidate]), \
         patch.object(pipeline, "verify_candidates", return_value=[]), \
         patch.object(pipeline, "best_match", return_value=None):
        result = pipeline.run_pipeline("irrelevant.jpg")

    assert result.success is False
    stage_names = [s.name for s in result.stages]
    assert stage_names == ["face_identification", "web_search", "match_verification"]
    assert result.stages[-1].status == "failed"


def test_pipeline_full_success_path_registers_and_reverifies():
    fake_face = MagicMock(crop="crop", confidence=0.9)
    fake_embedding = MagicMock(vector=[0.1, 0.2])
    candidate = SearchCandidate(title="t", link="https://x.com/p", source="x.com", thumbnail="t", position=0)
    match = VerifiedMatch(candidate=candidate, face_distance=0.05, is_face_match=True, confidence=0.95)

    fake_submitted = MagicMock(record_id=42, tx_hash="0xabc", explorer_url="https://amoy.polygonscan.com/tx/0xabc")
    fake_chain_client = MagicMock()
    fake_chain_client.register_record.return_value = fake_submitted
    fake_chain_client.verify_hash.return_value = True

    with patch.object(pipeline, "detect_primary_face", return_value=fake_face), \
         patch.object(pipeline, "encode_face", return_value=fake_embedding), \
         patch.object(pipeline, "reverse_image_search", return_value=[candidate]), \
         patch.object(pipeline, "filter_social_candidates", return_value=[candidate]), \
         patch.object(pipeline, "verify_candidates", return_value=[match]), \
         patch.object(pipeline, "best_match", return_value=match), \
         patch.object(pipeline, "_sha256_file", return_value="deadbeef"), \
         patch.object(pipeline, "pin_json", return_value="Qmfakecid"), \
         patch.object(pipeline, "ChainClient", return_value=fake_chain_client):
        result = pipeline.run_pipeline("irrelevant.jpg")

    assert result.success is True
    assert result.ipfs_cid == "Qmfakecid"
    assert result.record_id == 42
    assert result.reverify_ok is True
    stage_names = [s.name for s in result.stages]
    assert stage_names == [
        "face_identification",
        "web_search",
        "match_verification",
        "ipfs_storage",
        "blockchain_registration",
        "re_verification",
    ]
    assert all(s.status == "success" for s in result.stages)
