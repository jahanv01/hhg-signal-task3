"""HH Goa-themed Streamlit UI for the face -> web search -> blockchain
verification pipeline. Run with: streamlit run app/streamlit_app.py
"""
import os
import sys
import tempfile

import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.blockchain.chain_client import ChainClient, ChainClientError
from src.blockchain.hasher import hash_bundle, hash_bundle_hex
from src.certificate.generate import generate_certificate
from src.pipeline import STAGE_ORDER, run_pipeline

STAGE_LABELS = {
    "face_identification": ("🧑‍💻", "Face Identification"),
    "web_search": ("🔎", "Web / Social Search"),
    "match_verification": ("🧬", "Match Verification"),
    "ipfs_storage": ("🗂️", "IPFS Evidence Storage"),
    "blockchain_registration": ("🪙", "Blockchain Registration"),
    "re_verification": ("🔁", "Re-Verification"),
}

STATUS_ICON = {"pending": "○", "active": "◐", "success": "✔", "failed": "✕"}

st.set_page_config(page_title="HH Signal — Face Verification Pipeline", page_icon="🌴", layout="wide")


def inject_theme():
    css_path = os.path.join(os.path.dirname(__file__), "theme.css")
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="hhg-floaters">
            <div class="floater floater-1">🌴</div>
            <div class="floater floater-2">🌊</div>
            <div class="floater floater-3">⛵</div>
            <div class="floater floater-4">🌅</div>
            <div class="floater floater-5">🧭</div>
            <div class="floater floater-6">✨</div>
        </div>
        <div class="hhg-wave-line"></div>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    st.markdown(
        """
        <div class="hhg-header">
            <span class="hhg-badge">HH GOA 2026 · SIGNAL TASK 3</span>
            <h1 class="hhg-title">FACE → SEARCH → CHAIN</h1>
            <div class="hhg-tagline">Less Noise. More Signal. — face identification, genuine web search,
            and tamper-evident blockchain verification, live.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stage_row(placeholder, stage_key: str, state: str, message: str = ""):
    icon, label = STAGE_LABELS[stage_key]
    status_icon = STATUS_ICON.get(state, "○")
    placeholder.markdown(
        f"""
        <div class="stage-row {state}">
            <div class="stage-icon">{icon}</div>
            <div class="stage-text">
                <div class="stage-name">{status_icon} {label}</div>
                <div class="stage-msg">{message}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource(show_spinner=False)
def get_chain_client():
    return ChainClient()


def render_results(result):
    st.markdown("<br>", unsafe_allow_html=True)

    if not result.success or result.best_match is None:
        last_stage = result.stages[-1] if result.stages else None
        msg = last_stage.message if last_stage else "Unknown error"
        st.markdown(
            f"""<div class="hhg-card">
                <span class="hhg-pill pill-fail">NO VERIFIED MATCH</span>
                <p style="margin-top:10px;">{msg}</p>
                <p class="hhg-mono">This is expected behavior when the face has no genuinely
                matching, indexable social media presence — the pipeline reports this honestly
                rather than forcing a false positive.</p>
            </div>""",
            unsafe_allow_html=True,
        )
        return

    match = result.best_match
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            f"""<div class="hhg-card">
                <span class="hhg-pill pill-teal">MATCHED SOCIAL POST</span>
                <h3 style="margin:10px 0 4px 0;">{match.candidate.title or match.candidate.source}</h3>
                <p><a class="hhg-link" href="{match.candidate.link}" target="_blank">{match.candidate.link}</a></p>
                <span class="hhg-pill pill-gold">Face match confidence: {match.confidence:.1%}</span>
            </div>""",
            unsafe_allow_html=True,
        )
        try:
            st.image(match.candidate.thumbnail, width=260)
        except Exception:
            pass

    with col2:
        st.markdown(
            f"""<div class="hhg-card">
                <span class="hhg-pill pill-teal">ON-CHAIN RECORD — POLYGON AMOY</span>
                <p style="margin-top:10px;">Record #{result.record_id}</p>
                <p class="hhg-mono">tx: <a class="hhg-link" href="{result.explorer_url}" target="_blank">{result.tx_hash}</a></p>
                <p class="hhg-mono">IPFS CID: <a class="hhg-link" href="https://gateway.pinata.cloud/ipfs/{result.ipfs_cid}" target="_blank">{result.ipfs_cid}</a></p>
                <p class="hhg-mono">Data hash: {result.data_hash_hex}</p>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("#### Prove it live")
    c1, c2, c3 = st.columns([1, 1, 2])

    with c1:
        if st.button("🔁 Re-verify Now", use_container_width=True):
            try:
                client = get_chain_client()
                fresh_hash = hash_bundle(result.evidence_bundle)
                ok = client.verify_hash(result.record_id, fresh_hash)
                if ok:
                    st.success("Recomputed hash MATCHES the on-chain record. Data is untampered.")
                else:
                    st.error("Hash mismatch against on-chain record.")
            except ChainClientError as e:
                st.error(str(e))

    with c2:
        if st.button("⚠️ Run Tamper Test", use_container_width=True):
            tampered = dict(result.evidence_bundle)
            tampered["face_match_confidence"] = 0.01  # simulate an attacker altering the record
            try:
                client = get_chain_client()
                tampered_hash = hash_bundle(tampered)
                ok = client.verify_hash(result.record_id, tampered_hash)
                if not ok:
                    st.error("Tampered data hash does NOT match on-chain record — tamper detected, as expected.")
                else:
                    st.warning("Unexpected: tampered hash matched (should not happen).")
            except ChainClientError as e:
                st.error(str(e))

    with c3:
        st.markdown(
            f"""<p class="hhg-mono">Re-verify reads the on-chain record and recomputes the evidence
            hash locally to confirm nothing has changed. Tamper Test alters a copy of the data first
            to show the on-chain comparison catching it — that's the tamper-evidence the task asks for.</p>""",
            unsafe_allow_html=True,
        )

    st.markdown("#### Certificate")
    query_image_path = st.session_state.get("query_image_path")
    cert_path = os.path.join(tempfile.gettempdir(), f"hhg_certificate_{result.record_id}.png")
    if not os.path.exists(cert_path):
        generate_certificate(
            evidence_bundle=result.evidence_bundle,
            explorer_url=result.explorer_url,
            record_id=result.record_id,
            ipfs_cid=result.ipfs_cid,
            output_path=cert_path,
            query_image_path=query_image_path,
        )
    with open(cert_path, "rb") as f:
        st.download_button(
            "⬇ Download Verification Certificate",
            data=f.read(),
            file_name=f"hhg_verification_certificate_{result.record_id}.png",
            mime="image/png",
        )


def main():
    inject_theme()
    render_header()

    if "result" not in st.session_state:
        st.session_state.result = None

    left, right = st.columns([1, 1.3])

    with left:
        st.markdown('<div class="hhg-card">', unsafe_allow_html=True)
        st.markdown("##### Upload a face scan")
        uploaded = st.file_uploader("Upload a face scan", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
        if uploaded is not None:
            st.image(uploaded, width=240)
        run_clicked = st.button("▶ Run Verification Pipeline", use_container_width=True, disabled=uploaded is None)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("##### Pipeline status")
        placeholders = {stage: st.empty() for stage in STAGE_ORDER}
        for stage in STAGE_ORDER:
            render_stage_row(placeholders[stage], stage, "pending", "waiting...")

    if uploaded is not None and run_clicked:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded.name)[1]) as tmp:
            tmp.write(uploaded.getbuffer())
            tmp_path = tmp.name

        def on_start(stage_key: str):
            render_stage_row(placeholders[stage_key], stage_key, "active", "running...")

        def on_end(stage_result):
            state = "success" if stage_result.status == "success" else "failed"
            render_stage_row(placeholders[stage_result.name], stage_result.name, state, stage_result.message)

        result = run_pipeline(tmp_path, on_stage_start=on_start, on_stage_end=on_end)
        st.session_state.result = result
        st.session_state.query_image_path = tmp_path  # kept for certificate generation

    if st.session_state.result is not None:
        render_results(st.session_state.result)

    st.markdown(
        """<div style="text-align:center; margin-top:40px; opacity:0.4;" class="hhg-mono">
        Built for HH Goa 2026 · Signal Task 3 — Face Identification &amp; Blockchain Verification
        </div>""",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
