import os

from src.certificate.generate import generate_certificate

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_images")
FACE_IMAGE = os.path.join(SAMPLE_DIR, "test1.jpg")

BUNDLE = {
    "post_url": "https://www.reddit.com/r/example/comments/abc/",
    "post_source": "Reddit",
    "post_title": "Example matched post",
    "face_match_confidence": 0.93,
    "generated_at": "2026-09-07T00:00:00+00:00",
}


def test_generate_certificate_creates_a_png(tmp_path):
    output_path = str(tmp_path / "cert.png")

    result_path = generate_certificate(
        evidence_bundle=BUNDLE,
        explorer_url="https://amoy.polygonscan.com/tx/0xabc123",
        record_id=1,
        ipfs_cid="Qmfakecid",
        output_path=output_path,
        query_image_path=FACE_IMAGE,
    )

    assert result_path == output_path
    assert os.path.exists(output_path)
    assert os.path.getsize(output_path) > 1000  # not an empty/corrupt image


def test_generate_certificate_without_query_image(tmp_path):
    output_path = str(tmp_path / "cert_no_image.png")

    generate_certificate(
        evidence_bundle=BUNDLE,
        explorer_url="https://amoy.polygonscan.com/tx/0xabc123",
        record_id=1,
        ipfs_cid="Qmfakecid",
        output_path=output_path,
        query_image_path=None,
    )

    assert os.path.exists(output_path)
