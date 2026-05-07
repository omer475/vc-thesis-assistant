"""Streamlit web UI for the VC Thesis Assistant.

Run with:
    streamlit run src/app.py
"""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure the project root is on sys.path so `from src...` works when streamlit runs this file.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

# Streamlit Cloud stores secrets in st.secrets, not as env vars. Mirror them
# into os.environ before any module that reads env vars (anthropic SDK, our
# password gate, etc.) so the same code works on Render, Streamlit Cloud, and
# locally with .env files — no per-host conditional logic needed.
try:
    for _key in list(st.secrets.keys()):
        _val = st.secrets[_key]
        if isinstance(_val, str):
            os.environ.setdefault(_key, _val)
except Exception:
    pass  # no secrets file present (typical for local dev with .env)

import anthropic
from dotenv import load_dotenv

from src import bootstrap
from src.analyze import analyze_deck
from src.config import (
    ANALYSES_DIR,
    DB_PATH,
    DOCS_DIR,
    INCOMING_DECKS_DIR,
    PROFILE_PATH,
)
from src.ingest import SUPPORTED_EXTENSIONS, extract, init_db
from src.profile import (
    INSTRUCTIONS as PROFILE_INSTRUCTIONS,
    USER_PROMPT as PROFILE_USER_PROMPT,
    load_corpus,
)

load_dotenv()

# On the first request after a deploy/restart, copy committed example data
# into DATA_DIR so the deployed demo isn't empty. No-op in local dev.
bootstrap.run()

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

def get_corpus_summary() -> tuple[int, int]:
    """Return (doc_count, total_chars) from the SQLite store."""
    if not DB_PATH.exists():
        return 0, 0
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(LENGTH(content)), 0) FROM documents"
        ).fetchone()
        return int(row[0]), int(row[1])
    except sqlite3.OperationalError:
        return 0, 0
    finally:
        conn.close()


def list_corpus_documents() -> list[tuple[int, str, int, int, str]]:
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT id, filename, page_count, LENGTH(content), ingested_at "
            "FROM documents ORDER BY id"
        ).fetchall()
        return [(r[0], r[1], r[2], r[3], r[4]) for r in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def save_uploaded_file(uploaded_file, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / uploaded_file.name
    path.write_bytes(uploaded_file.getbuffer())
    return path


def ingest_one_file(path: Path) -> tuple[bool, str]:
    """Ingest a single file into the SQLite store. Returns (success, message)."""
    try:
        text, page_count = extract(path)
    except Exception as e:
        return False, f"failed to read ({e})"

    if not text:
        return False, "no extractable text (image-only PDF — needs vision in a later phase)"

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    try:
        conn.execute(
            "INSERT INTO documents (filename, page_count, content, ingested_at) "
            "VALUES (?, ?, ?, ?)",
            (path.name, page_count, text, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return True, f"ingested ({page_count} pages, {len(text):,} chars)"
    except sqlite3.IntegrityError:
        return False, "already ingested (filename matches an existing entry)"
    finally:
        conn.close()


def stream_profile_generation():
    """Generator that streams text from Claude while regenerating the firm profile.

    Saves to PROFILE_PATH on completion. Yields text deltas for st.write_stream.
    """
    conn = sqlite3.connect(DB_PATH)
    corpus = load_corpus(conn)
    conn.close()

    client = anthropic.Anthropic()
    chunks: list[str] = []
    final_message = None

    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=[
            {"type": "text", "text": PROFILE_INSTRUCTIONS},
            {
                "type": "text",
                "text": f"<firm_corpus>\n{corpus}\n</firm_corpus>",
                "cache_control": {"type": "ephemeral"},
            },
        ],
        messages=[{"role": "user", "content": PROFILE_USER_PROMPT}],
    ) as stream:
        for text in stream.text_stream:
            chunks.append(text)
            yield text
        final_message = stream.get_final_message()

    profile_text = "".join(chunks)
    PROFILE_PATH.write_text(profile_text)

    if final_message:
        usage = final_message.usage
        st.session_state["last_profile_usage"] = {
            "input": usage.input_tokens,
            "cache_write": usage.cache_creation_input_tokens,
            "cache_read": usage.cache_read_input_tokens,
            "output": usage.output_tokens,
        }


def run_deal_analysis(
    deck_path: Path, streaming_placeholder
) -> dict:
    """Run analyze_deck() with live streaming into the given Streamlit placeholder.

    Saves both the full memo and the triage block to disk, populates session
    state with the structured result, and returns it.
    """
    deck_text = deck_path.read_text(encoding="utf-8")
    profile_text = PROFILE_PATH.read_text(encoding="utf-8")

    conn = sqlite3.connect(DB_PATH)
    corpus = load_corpus(conn)
    conn.close()

    chunks: list[str] = []

    def on_chunk(text: str) -> None:
        chunks.append(text)
        streaming_placeholder.markdown("".join(chunks))

    result = analyze_deck(
        deck_text=deck_text,
        deck_filename=deck_path.name,
        profile_text=profile_text,
        corpus_text=corpus,
        stream_callback=on_chunk,
    )

    ANALYSES_DIR.mkdir(parents=True, exist_ok=True)
    memo_path = ANALYSES_DIR / f"{deck_path.stem}.memo.md"
    triage_path = ANALYSES_DIR / f"{deck_path.stem}.triage.md"
    memo_path.write_text(result["full_memo_md"])
    triage_path.write_text(result["triage_md"])

    st.session_state["last_analysis"] = result
    st.session_state["last_deck_path"] = str(deck_path)
    st.session_state["last_memo_path"] = str(memo_path)

    return result


def render_triage(result: dict, deck_path: Path | None) -> None:
    """Render the structured triage layout for a completed analysis.

    Layout (top → bottom):
      - colored verdict badge
      - WHY bullets
      - ASK FIRST questions (only if verdict == 'Ask first')
      - full-memo expander (deep dive)
      - token-usage caption
      - download button
    """
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

    if deck_path and full_memo:
        st.download_button(
            "Download full memo (.md)",
            data=full_memo,
            file_name=f"{Path(deck_path).stem}.memo.md",
            mime="text/markdown",
        )


# ----- UI ---------------------------------------------------------------------

st.title("VC Thesis Assistant")
st.caption("Drop in a deck. Get back a memo grounded in your firm's history.")

with st.sidebar:
    st.header("Status")
    doc_count, total_chars = get_corpus_summary()
    st.metric("Documents in corpus", doc_count)
    st.metric("Total characters", f"{total_chars:,}")
    profile_exists = PROFILE_PATH.exists()
    st.metric("Firm profile", "Generated" if profile_exists else "Not generated")
    st.divider()
    st.caption(
        "Model: claude-opus-4-7  \n"
        "Adaptive thinking + prompt caching enabled."
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
                path = save_uploaded_file(f, DOCS_DIR)
                ok, msg = ingest_one_file(path)
                results.append((f.name, ok, msg))
            for name, ok, msg in results:
                if ok:
                    st.success(f"{name}: {msg}")
                else:
                    st.warning(f"{name}: {msg}")
            st.rerun()

    st.divider()
    st.subheader("Current corpus")
    docs = list_corpus_documents()
    if not docs:
        st.info("No documents yet. Upload above to get started.")
    else:
        st.dataframe(
            [
                {
                    "ID": d[0],
                    "Filename": d[1],
                    "Pages": d[2],
                    "Chars": d[3],
                    "Ingested": d[4][:19].replace("T", " "),
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
            placeholder.write_stream(stream_profile_generation())
        usage = st.session_state.get("last_profile_usage")
        if usage:
            st.caption(
                f"Tokens — input: {usage['input']:,} | "
                f"cache write: {usage['cache_write']:,} | "
                f"cache read: {usage['cache_read']:,} | "
                f"output: {usage['output']:,}"
            )

    if PROFILE_PATH.exists() and not gen_clicked:
        with st.expander("View current firm profile", expanded=False):
            st.markdown(PROFILE_PATH.read_text())


# ----- Tab 2: Analyze a deal --------------------------------------------------

with tab_analyze:
    if not PROFILE_PATH.exists():
        st.warning(
            "No firm profile yet. Go to the **Firm Setup** tab, upload some docs, "
            "and generate the profile first."
        )
    else:
        st.subheader("Analyze a new pitch deck")
        st.write(
            "Upload a deck (or pick one of the test decks already in the project). "
            "The analyzer will read it, compare against the firm's history, and "
            "write a one-page fit memo."
        )

        deck_choice = st.radio(
            "Deck source",
            options=["Upload a new deck", "Pick a test deck from disk"],
            horizontal=True,
        )

        target_deck_path: Path | None = None

        if deck_choice == "Upload a new deck":
            deck_file = st.file_uploader(
                "Drop a pitch deck",
                type=[ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS],
                accept_multiple_files=False,
                key="deck_upload",
            )
            if deck_file is not None:
                target_deck_path = save_uploaded_file(deck_file, INCOMING_DECKS_DIR)
                st.caption(f"Saved to {target_deck_path}")
        else:
            existing = sorted(
                p
                for p in INCOMING_DECKS_DIR.iterdir()
                if p.suffix.lower() in SUPPORTED_EXTENSIONS
            ) if INCOMING_DECKS_DIR.exists() else []
            if not existing:
                st.info("No test decks on disk yet.")
            else:
                pick = st.selectbox(
                    "Select a deck",
                    options=[p.name for p in existing],
                )
                target_deck_path = INCOMING_DECKS_DIR / pick

        if target_deck_path is not None:
            with st.expander("Preview the deck", expanded=False):
                st.markdown(target_deck_path.read_text(encoding="utf-8"))

            if st.button("Analyze this deck", type="primary"):
                with st.spinner("Reading the deck and writing the memo..."):
                    streaming_placeholder = st.empty()
                    run_deal_analysis(target_deck_path, streaming_placeholder)
                    streaming_placeholder.empty()

        if "last_analysis" in st.session_state:
            st.divider()
            stored_deck = st.session_state.get("last_deck_path")
            render_triage(
                st.session_state["last_analysis"],
                Path(stored_deck) if stored_deck else None,
            )
