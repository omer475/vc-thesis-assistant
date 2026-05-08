"""Streamlit web UI for the VC Thesis Assistant.

Run with:
    streamlit run src/app.py

After Step 2 of Phase 1: all firm/deck/analysis data lives in Supabase.
Local files in `data/` are committed example fixtures (auto-seeded into
the DB on first boot) and convenience exports for CLI users.
"""

from __future__ import annotations

import os
import sys
from io import BytesIO
from pathlib import Path

# Ensure the project root is on sys.path so `from src...` works when streamlit runs this file.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

# Streamlit Cloud stores secrets in st.secrets, not as env vars. Mirror them
# into os.environ before any module that reads env vars (anthropic SDK,
# supabase client, our password gate) so the same code runs on Streamlit
# Cloud and locally with .env files — no per-host conditional logic.
try:
    for _key in list(st.secrets.keys()):
        _val = st.secrets[_key]
        if isinstance(_val, str):
            os.environ.setdefault(_key, _val)
except Exception:
    pass  # no secrets file present (typical for local dev with .env)

from dotenv import load_dotenv
from pypdf import PdfReader

from src import bootstrap, db
from src.analyze import run_analysis
from src.config import INCOMING_DECKS_DIR
from src.ingest import SUPPORTED_EXTENSIONS
from src.profile import generate_profile

load_dotenv()

# First request after a deploy: ensure the default firm exists in Supabase
# and seed example fixtures on first boot. Idempotent on every subsequent run.
_boot_info = bootstrap.run()
FIRM_ID: str = _boot_info["firm_id"]


st.set_page_config(
    page_title="VC Thesis Assistant",
    page_icon="V",
    layout="wide",
)


def _require_password() -> None:
    """If APP_PASSWORD is set in the environment, gate the app behind it."""
    expected = os.environ.get("APP_PASSWORD", "").strip()
    if not expected:
        return
    if st.session_state.get("_authed"):
        return

    st.title("VC Thesis Assistant")
    st.caption("Enter the access password to continue.")
    pw = st.text_input("Password", type="password", key="_pw_input")
    if pw == "":
        st.stop()
    if pw == expected:
        st.session_state["_authed"] = True
        st.rerun()
    else:
        st.error("Wrong password.")
        st.stop()


_require_password()


# ----- helpers -----------------------------------------------------------------


def extract_uploaded_file(uploaded_file) -> tuple[str, int]:
    """Extract text from a Streamlit UploadedFile in memory (no disk write).

    Returns (text, page_count). Streamlit Cloud's filesystem is ephemeral, so
    persisting uploads to disk has no value — the source of truth is Supabase.
    """
    name = uploaded_file.name
    suffix = Path(name).suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(BytesIO(uploaded_file.getvalue()))
        pages = [(p.extract_text() or "") for p in reader.pages]
        return "\n\n".join(pages).strip(), len(reader.pages)
    if suffix in {".md", ".txt"}:
        text = uploaded_file.getvalue().decode("utf-8", errors="replace").strip()
        return text, max(1, text.count("\n\n") // 5 + 1)
    raise ValueError(f"Unsupported file type: {suffix}")


def ingest_uploaded_file(uploaded_file) -> tuple[bool, str]:
    """Extract + insert one uploaded file into the firm's corpus.
    Returns (success, message).
    """
    try:
        text, page_count = extract_uploaded_file(uploaded_file)
    except Exception as e:
        return False, f"failed to read ({e})"
    if not text:
        return False, "no extractable text (image-only PDF — needs vision in a later phase)"
    row = db.insert_document(FIRM_ID, uploaded_file.name, text, page_count)
    if row is None:
        return False, "already ingested (filename matches an existing entry)"
    return True, f"ingested ({page_count} pages, {len(text):,} chars)"


def stream_profile_generation_to(placeholder) -> dict:
    """Stream profile generation, updating the given Streamlit placeholder.
    Returns the result dict (with usage)."""
    chunks: list[str] = []

    def on_chunk(text: str) -> None:
        chunks.append(text)
        placeholder.markdown("".join(chunks))

    return generate_profile(FIRM_ID, stream_callback=on_chunk)


def run_deal_analysis_streamed(
    deck_text: str, deck_filename: str, source: str, placeholder
) -> dict:
    """Run analysis with live streaming into the given placeholder.
    Saves to session_state and returns the result."""
    chunks: list[str] = []

    def on_chunk(text: str) -> None:
        chunks.append(text)
        placeholder.markdown("".join(chunks))

    result = run_analysis(
        FIRM_ID,
        deck_text=deck_text,
        deck_filename=deck_filename,
        source=source,
        stream_callback=on_chunk,
    )
    st.session_state["last_analysis"] = result
    st.session_state["last_deck_filename"] = deck_filename
    return result


def render_triage(result: dict, deck_filename: str | None) -> None:
    """Render the structured triage layout for a completed analysis."""
    verdict = result.get("verdict", "Unknown")

    if verdict == "Take meeting":
        st.success("##### VERDICT — Take meeting")
    elif verdict == "Pass":
        st.error("##### VERDICT — Pass")
    elif verdict == "Ask first":
        st.warning("##### VERDICT — Ask first")
    else:
        st.info(f"##### VERDICT — {verdict}")

    st.markdown("**Why**")
    bullets = result.get("bullets") or []
    if bullets:
        for b in bullets:
            st.markdown(f"- {b.get('text', '')}")
    else:
        st.caption("(no bullets parsed)")

    questions = result.get("questions")
    if questions:
        st.markdown("**Ask first**")
        for i, q in enumerate(questions, 1):
            st.markdown(f"{i}. {q}")

    full_memo = result.get("full_memo_md", "")
    if full_memo:
        with st.expander("Full memo — deeper analysis", expanded=False):
            st.markdown(full_memo)

    usage = result.get("usage") or {}
    if usage:
        st.caption(
            f"Tokens — input: {usage.get('input_tokens', 0):,}  ·  "
            f"cache read: {usage.get('cache_read_input_tokens', 0):,}  ·  "
            f"cache write: {usage.get('cache_creation_input_tokens', 0):,}  ·  "
            f"output: {usage.get('output_tokens', 0):,}  ·  "
            f"latency: {usage.get('latency_ms', 0):,} ms"
        )

    if deck_filename and full_memo:
        st.download_button(
            "Download full memo (.md)",
            data=full_memo,
            file_name=f"{Path(deck_filename).stem}.memo.md",
            mime="text/markdown",
        )


# ----- UI ---------------------------------------------------------------------

st.title("VC Thesis Assistant")
st.caption("Drop in a deck. Get back a memo grounded in your firm's history.")

# Sidebar: status snapshot. Hits Supabase on every script rerun (cheap).
with st.sidebar:
    st.header("Status")
    doc_count = db.count_documents(FIRM_ID)
    total_chars = db.total_corpus_chars(FIRM_ID)
    profile_md = db.get_firm_profile(FIRM_ID)
    st.metric("Documents in corpus", doc_count)
    st.metric("Total characters", f"{total_chars:,}")
    st.metric("Firm profile", "Generated" if profile_md else "Not generated")
    st.divider()
    st.caption(
        "Model: claude-opus-4-7  \n"
        "Adaptive thinking + prompt caching enabled.  \n"
        "Database: Supabase Postgres."
    )


tab_setup, tab_analyze = st.tabs(["1. Firm Setup", "2. Analyze a Deal"])


# ----- Tab 1: Firm Setup ------------------------------------------------------

with tab_setup:
    st.subheader("Add the firm's documents")
    st.write(
        "Upload investment memos, thesis docs, pass-reason notes, anything that "
        "captures how this firm thinks. Supported types: "
        f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}."
    )

    uploaded = st.file_uploader(
        "Drop documents here",
        type=[ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS],
        accept_multiple_files=True,
        key="firm_doc_upload",
    )

    if uploaded:
        if st.button("Save and ingest", type="primary"):
            results = []
            for f in uploaded:
                ok, msg = ingest_uploaded_file(f)
                results.append((f.name, ok, msg))
            for name, ok, msg in results:
                if ok:
                    st.success(f"{name}: {msg}")
                else:
                    st.warning(f"{name}: {msg}")
            st.rerun()

    st.divider()
    st.subheader("Current corpus")
    docs = db.list_documents(FIRM_ID)
    if not docs:
        st.info("No documents yet. Upload above to get started.")
    else:
        st.dataframe(
            [
                {
                    "Filename": d["filename"],
                    "Pages": d["page_count"],
                    "Chars": len(d.get("content") or ""),
                    "Ingested": d["ingested_at"][:19].replace("T", " "),
                }
                for d in docs
            ],
            hide_index=True,
            use_container_width=True,
        )

    st.divider()
    st.subheader("Firm strategy profile")
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        gen_clicked = st.button(
            "Generate / regenerate profile",
            type="primary",
            disabled=doc_count == 0,
        )

    if gen_clicked:
        with st.spinner("Distilling the firm's strategy..."):
            placeholder = st.empty()
            result = stream_profile_generation_to(placeholder)
            placeholder.empty()
        usage = result["usage"]
        st.success("Profile generated and saved to Supabase.")
        st.caption(
            f"Tokens — input: {usage['input_tokens']:,}  ·  "
            f"cache write: {usage['cache_creation_input_tokens']:,}  ·  "
            f"cache read: {usage['cache_read_input_tokens']:,}  ·  "
            f"output: {usage['output_tokens']:,}"
        )
        with st.expander("View generated firm profile", expanded=True):
            st.markdown(result["profile_md"])
    elif profile_md:
        with st.expander("View current firm profile", expanded=False):
            st.markdown(profile_md)


# ----- Tab 2: Analyze a deal --------------------------------------------------

with tab_analyze:
    if not profile_md:
        st.warning(
            "No firm profile yet. Go to the **Firm Setup** tab, upload some docs, "
            "and generate the profile first."
        )
    else:
        st.subheader("Analyze a new pitch deck")
        st.write(
            "Upload a deck (or pick one of the test decks already in the project). "
            "The analyzer compares it against the firm's history and writes a "
            "compact triage block plus a deeper memo."
        )

        deck_choice = st.radio(
            "Deck source",
            options=["Upload a new deck", "Pick a test deck from disk"],
            horizontal=True,
        )

        # Tuple shape: (source, filename, text) once a deck is picked
        target_deck: tuple[str, str, str] | None = None

        if deck_choice == "Upload a new deck":
            deck_file = st.file_uploader(
                "Drop a pitch deck",
                type=[ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS],
                accept_multiple_files=False,
                key="deck_upload",
            )
            if deck_file is not None:
                try:
                    deck_text, _ = extract_uploaded_file(deck_file)
                except Exception as e:
                    st.error(f"Could not read deck: {e}")
                    deck_text = ""
                if deck_text:
                    target_deck = ("upload", deck_file.name, deck_text)
        else:
            existing = (
                sorted(
                    p
                    for p in INCOMING_DECKS_DIR.iterdir()
                    if p.suffix.lower() in SUPPORTED_EXTENSIONS
                )
                if INCOMING_DECKS_DIR.exists()
                else []
            )
            if not existing:
                st.info("No test decks on disk yet.")
            else:
                pick = st.selectbox(
                    "Select a deck",
                    options=[p.name for p in existing],
                )
                p = INCOMING_DECKS_DIR / pick
                target_deck = ("upload", p.name, p.read_text(encoding="utf-8"))

        if target_deck is not None:
            source, deck_filename, deck_text = target_deck
            with st.expander("Preview the deck", expanded=False):
                st.markdown(deck_text)

            if st.button("Analyze this deck", type="primary"):
                with st.spinner("Reading the deck and writing the memo..."):
                    streaming_placeholder = st.empty()
                    run_deal_analysis_streamed(
                        deck_text, deck_filename, source, streaming_placeholder
                    )
                    streaming_placeholder.empty()

        if "last_analysis" in st.session_state:
            st.divider()
            render_triage(
                st.session_state["last_analysis"],
                st.session_state.get("last_deck_filename"),
            )
