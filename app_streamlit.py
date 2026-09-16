"""
G1Saathi — Streamlit Application
Wraps the G1Saathi core (ingest, rag_chain, models) with:
  - Professional dark healthcare UI
  - Safety screening (emergency detection)
  - Structured logging
  - Multi-page navigation
  - Healthcare disclaimer

Entry point: streamlit run app.py
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path

import streamlit as st

# ── Logging — must be first ───────────────────────────────────────────────────
from logging_config import setup_logging

_LOG_DIR = Path("logs")
setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"), log_dir=_LOG_DIR)
logger = logging.getLogger(__name__)
logger.info("G1Saathi starting up (Python %s.%s)", sys.version_info.major, sys.version_info.minor)

# ── Upstream core ─────────────────────────────────────────────────────────────
from ingest import clear_index, ingest
from models import PROVIDER
from rag_chain import answer
from safety import screen as safety_screen

# ── Constants ─────────────────────────────────────────────────────────────────
UPLOAD_DIR = "data/uploads"
PERSIST_DIR = "chroma_db"
APP_VERSION = "1.0.0"

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="G1Saathi — AI Healthcare Assistant",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": f"G1Saathi v{APP_VERSION} — Agentic AI Healthcare Assistant"},
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --mp-bg:        #0f1117;
    --mp-surface:   #1a1d2e;
    --mp-surface2:  #232740;
    --mp-border:    #2d3252;
    --mp-accent:    #4f8ef7;
    --mp-accent-dk: #1e3a8a;
    --mp-green:     #22c55e;
    --mp-amber:     #f59e0b;
    --mp-red:       #ef4444;
    --mp-text:      #e2e8f0;
    --mp-muted:     #64748b;
    --mp-radius:    12px;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background-color: var(--mp-bg) !important;
    color: var(--mp-text) !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: var(--mp-surface) !important;
    border-right: 1px solid var(--mp-border);
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }

/* Chat messages */
[data-testid="stChatMessage"] {
    background-color: var(--mp-surface) !important;
    border: 1px solid var(--mp-border);
    border-radius: var(--mp-radius);
    padding: 1rem 1.25rem;
    margin-bottom: 0.6rem;
}

/* Chat input */
[data-testid="stChatInput"] {
    background-color: var(--mp-surface2) !important;
    border: 1px solid var(--mp-border) !important;
    border-radius: var(--mp-radius) !important;
}

/* Cards */
.mp-card {
    background: var(--mp-surface);
    border: 1px solid var(--mp-border);
    border-radius: var(--mp-radius);
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
}
.mp-card-title {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--mp-muted);
    margin-bottom: 0.5rem;
}

/* Badges */
.badge {
    display: inline-block;
    padding: 0.15rem 0.55rem;
    border-radius: 99px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.04em;
}
.badge-green  { background:#14532d; color:var(--mp-green);  }
.badge-amber  { background:#451a03; color:var(--mp-amber);  }
.badge-blue   { background:#1e3a8a; color:var(--mp-accent); }
.badge-red    { background:#450a0a; color:var(--mp-red);    }

/* Document chips */
.doc-chip {
    display: inline-block;
    background: var(--mp-accent-dk);
    color: var(--mp-accent);
    border-radius: 99px;
    padding: 3px 11px;
    margin: 2px 3px 2px 0;
    font-size: 0.78rem;
    font-weight: 500;
}

/* Healthcare disclaimer */
.disclaimer {
    background: var(--mp-surface);
    border-left: 3px solid var(--mp-amber);
    border-radius: 0 var(--mp-radius) var(--mp-radius) 0;
    padding: 0.7rem 0.9rem;
    font-size: 0.74rem;
    color: #94a3b8;
    margin-top: 0.5rem;
    line-height: 1.5;
}

/* Source expander */
.source-row {
    background: var(--mp-surface2);
    border: 1px solid var(--mp-border);
    border-radius: 8px;
    padding: 0.6rem 0.8rem;
    margin-bottom: 0.4rem;
    font-size: 0.82rem;
}

/* Divider */
.mp-hr { border: none; border-top: 1px solid var(--mp-border); margin: 0.8rem 0; }

/* Section header */
.section-header {
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 0.2rem;
}
.section-sub {
    font-size: 0.84rem;
    color: var(--mp-muted);
    margin-bottom: 1.2rem;
}

/* Thinking dots */
@keyframes pulse {
  0%,100%{opacity:1;} 50%{opacity:.3;}
}
.dot { display:inline-block; width:7px; height:7px; border-radius:50%;
       background:var(--mp-accent); margin:0 2px;
       animation:pulse 1.2s ease-in-out infinite; }
.dot:nth-child(2){animation-delay:.2s}
.dot:nth-child(3){animation-delay:.4s}

/* Buttons */
div.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Session state ─────────────────────────────────────────────────────────────
st.session_state.setdefault("messages", [])
st.session_state.setdefault("indexed_files", [])
st.session_state.setdefault("scan_warnings", [])
st.session_state.setdefault("last_sources", [])
st.session_state.setdefault("active_page", "ask")


# ── Helper: is an index loaded? ───────────────────────────────────────────────
def _is_indexed() -> bool:
    return os.path.isdir(PERSIST_DIR) and bool(st.session_state.indexed_files)


# ── Sidebar ───────────────────────────────────────────────────────────────────
def _render_sidebar():
    with st.sidebar:
        # Logo
        st.markdown(
            "<h2 style='color:#4f8ef7;margin:0;font-size:1.35rem;'>🩺 G1Saathi</h2>"
            "<p style='color:#64748b;font-size:0.73rem;margin:2px 0 1rem;'>"
            "Agentic AI Healthcare Assistant</p>",
            unsafe_allow_html=True,
        )
        st.markdown("<hr class='mp-hr'>", unsafe_allow_html=True)

        # Navigation
        pages = [
            ("ask",      "💬", "Ask"),
            ("reports",  "📄", "Medical Reports"),
            ("sources",  "📚", "Knowledge Sources"),
            ("system",   "⚙️", "System"),
        ]
        for key, icon, label in pages:
            active = st.session_state.active_page == key
            style = "background:#1e3a8a;color:#4f8ef7;" if active else ""
            if st.button(
                f"{icon}  {label}",
                key=f"nav_{key}",
                use_container_width=True,
            ):
                st.session_state.active_page = key
                st.rerun()

        st.markdown("<hr class='mp-hr'>", unsafe_allow_html=True)

        # Provider badge
        st.markdown(
            f"<div class='mp-card'>"
            f"<div class='mp-card-title'>LLM Provider</div>"
            f"<span class='badge badge-blue'>{PROVIDER.upper()}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Index status
        if _is_indexed():
            st.markdown(
                "<div class='mp-card'>"
                "<div class='mp-card-title'>Indexed Documents</div>",
                unsafe_allow_html=True,
            )
            chips = "".join(
                f"<span class='doc-chip'>{f}</span>"
                for f in st.session_state.indexed_files
            )
            st.markdown(chips, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # Disclaimer
        st.markdown(
            "<div class='disclaimer'>"
            "G1Saathi provides general healthcare <strong>information only</strong> "
            "and is not a substitute for diagnosis, treatment, or professional "
            "medical advice. For emergencies or severe symptoms, seek appropriate "
            "medical care <strong>immediately</strong>."
            "</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            f"<p style='color:#1f2937;font-size:0.62rem;text-align:center;margin-top:1rem;'>"
            f"v{APP_VERSION} · Python {sys.version_info.major}.{sys.version_info.minor}</p>",
            unsafe_allow_html=True,
        )


# ── Page: Ask ─────────────────────────────────────────────────────────────────
def _page_ask():
    col_main, col_right = st.columns([3, 1], gap="large")

    with col_main:
        st.markdown(
            "<div class='section-header'>💬 Ask G1Saathi</div>"
            "<div class='section-sub'>"
            "Upload medical PDFs in the sidebar, index them, then ask questions. "
            "Every answer cites the source document and page.</div>",
            unsafe_allow_html=True,
        )

        if not _is_indexed():
            st.markdown(
                "<div class='mp-card' style='text-align:center;padding:2.5rem 1rem;'>"
                "<div style='font-size:2.5rem;'>📄</div>"
                "<div style='font-size:1rem;font-weight:500;color:#94a3b8;margin:.5rem 0;'>"
                "No documents indexed yet</div>"
                "<div style='font-size:0.82rem;color:#64748b;'>"
                "Go to <b>Medical Reports</b> to upload PDFs, then come back here to ask questions."
                "</div></div>",
                unsafe_allow_html=True,
            )
            return

        # Conversation history
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if question := st.chat_input("Ask a question about your documents…"):
            _handle_query(question)

    with col_right:
        _panel_sources()


def _handle_query(question: str):
    question = question.strip()
    if not question:
        return

    logger.info("Query received — length=%d", len(question))

    # Safety screen
    safety = safety_screen(question)

    # Append user message
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown(
            "<span class='dot'></span><span class='dot'></span><span class='dot'></span>",
            unsafe_allow_html=True,
        )

        with st.spinner(""):
            result = answer(question, PERSIST_DIR)

        # Build final response
        parts = []
        if safety["safety_note"]:
            parts.append(safety["safety_note"])
        parts.append(result["answer"])
        final_text = "\n\n".join(parts)

        placeholder.markdown(final_text)

        # Inline source expander (upstream style, dark-themed)
        if result["sources"]:
            with st.expander(f"📎 Sources ({len(result['sources'])})"):
                for s in result["sources"]:
                    score_txt = f" · match {s['score']}" if s.get("score") is not None else ""
                    st.markdown(
                        f"<div class='source-row'>"
                        f"<strong>{s['file']}, p. {s['page']}</strong>{score_txt}<br>"
                        f"<span style='color:#94a3b8;font-size:0.78rem;'>{s['excerpt']}…</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

    st.session_state.messages.append({"role": "assistant", "content": final_text})
    st.session_state.last_sources = result.get("sources", [])

    logger.info(
        "Response delivered — sources=%d safety=%s",
        len(result.get("sources", [])),
        safety["risk_level"],
    )


def _panel_sources():
    st.markdown(
        "<div class='mp-card'><div class='mp-card-title'>📎 Last Sources</div>",
        unsafe_allow_html=True,
    )
    sources = st.session_state.last_sources
    if sources:
        for s in sources:
            score = f" ({s['score']})" if s.get("score") is not None else ""
            st.markdown(
                f"<div style='font-size:0.78rem;color:#94a3b8;padding:2px 0;'>"
                f"• {s['file']}, p. {s['page']}{score}</div>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            "<span style='color:#64748b;font-size:0.78rem;'>"
            "No sources yet — ask a question.</span>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


# ── Page: Medical Reports (Upload + Index) ────────────────────────────────────
def _page_reports():
    st.markdown(
        "<div class='section-header'>📄 Medical Reports</div>"
        "<div class='section-sub'>Upload PDF documents and build the knowledge index.</div>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([2, 1], gap="large")

    with col1:
        uploaded = st.file_uploader(
            "Upload medical PDFs",
            type=["pdf"],
            accept_multiple_files=True,
            help="Guidelines, research papers, clinical notes — text-based PDFs only.",
        )

        c1, c2 = st.columns(2)
        with c1:
            if st.button(
                "⚡ Index uploaded PDFs",
                type="primary",
                disabled=not uploaded,
                use_container_width=True,
            ):
                _do_index(uploaded)

        with c2:
            if st.button(
                "🗑️ Clear index",
                disabled=not _is_indexed(),
                use_container_width=True,
            ):
                _do_clear_index()

        if st.session_state.scan_warnings:
            st.warning(
                "⚠️ No readable text in: "
                + ", ".join(st.session_state.scan_warnings)
                + ". These may be scanned images — run OCR (e.g. `ocrmypdf`) before uploading."
            )

    with col2:
        st.markdown(
            "<div class='mp-card'>"
            "<div class='mp-card-title'>How it works</div>"
            "<ol style='font-size:0.82rem;color:#94a3b8;padding-left:1.1rem;margin:0;'>"
            "<li>PDFs are split into overlapping chunks</li>"
            "<li>Each chunk is embedded into <strong>Chroma</strong></li>"
            "<li>At query time, top-K chunks are retrieved</li>"
            "<li>The LLM answers <em>only</em> from those chunks</li>"
            "<li>Every claim is cited with file + page</li>"
            "</ol>"
            "</div>",
            unsafe_allow_html=True,
        )
        if _is_indexed():
            st.markdown(
                "<div class='mp-card'>"
                "<div class='mp-card-title'>Active Knowledge Base</div>",
                unsafe_allow_html=True,
            )
            for f in st.session_state.indexed_files:
                st.markdown(
                    f"<span class='doc-chip'>{f}</span>", unsafe_allow_html=True
                )
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown(
                "<div class='mp-card'><div class='mp-card-title'>Status</div>"
                "<span class='badge badge-amber'>No index</span>"
                "<p style='font-size:0.78rem;color:#64748b;margin:.5rem 0 0;'>"
                "Upload and index PDFs to enable Q&amp;A.</p></div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            "<div class='mp-card'><div class='mp-card-title'>Sample Documents</div>"
            "<p style='font-size:0.78rem;color:#94a3b8;'>"
            "Two synthetic sample papers are included in <code>examples/</code> — "
            "upload them to test the system without your own documents.</p></div>",
            unsafe_allow_html=True,
        )


def _do_index(uploaded):
    shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    paths = []
    for f in uploaded:
        p = os.path.join(UPLOAD_DIR, f.name)
        with open(p, "wb") as fh:
            fh.write(f.getbuffer())
        paths.append(p)

    logger.info("Indexing %d file(s): %s", len(paths), [os.path.basename(p) for p in paths])
    with st.spinner(f"Indexing {len(paths)} file(s)…"):
        n_chunks, warnings = ingest(paths, PERSIST_DIR, reset=True)

    st.session_state.indexed_files = [os.path.basename(p) for p in paths]
    st.session_state.scan_warnings = warnings
    st.session_state.messages = []  # stale chat refers to old docs
    st.session_state.last_sources = []

    if n_chunks:
        logger.info("Indexed %d chunks from %d file(s)", n_chunks, len(paths))
        st.success(f"✅ Indexed **{n_chunks} chunks** from {len(paths)} file(s). "
                   "Go to **Ask** to start querying.")
    else:
        st.error("❌ No extractable text found. See the scanned-PDF warning above.")
    st.rerun()


def _do_clear_index():
    clear_index(PERSIST_DIR)
    shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
    st.session_state.indexed_files = []
    st.session_state.messages = []
    st.session_state.scan_warnings = []
    st.session_state.last_sources = []
    logger.info("Index cleared by user")
    st.rerun()


# ── Page: Knowledge Sources ───────────────────────────────────────────────────
def _page_sources():
    st.markdown(
        "<div class='section-header'>📚 Knowledge Sources</div>"
        "<div class='section-sub'>Overview of the current vector store state.</div>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        status = "Active" if _is_indexed() else "Empty"
        badge = "badge-green" if _is_indexed() else "badge-amber"
        st.markdown(
            f"<div class='mp-card'><div class='mp-card-title'>Vector Store</div>"
            f"<span class='badge {badge}'>{status}</span>"
            f"<p style='font-size:0.78rem;color:#64748b;margin:.4rem 0 0;'>Chroma (persistent)</p>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col2:
        model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text") if PROVIDER == "ollama" \
            else "text-embedding-3-small"
        st.markdown(
            f"<div class='mp-card'><div class='mp-card-title'>Embedding Model</div>"
            f"<span class='badge badge-blue'>{model}</span></div>",
            unsafe_allow_html=True,
        )
    with col3:
        n_docs = len(st.session_state.indexed_files)
        st.markdown(
            f"<div class='mp-card'><div class='mp-card-title'>Documents</div>"
            f"<span style='font-size:1.4rem;font-weight:700;color:#4f8ef7;'>{n_docs}</span>"
            f"<span style='font-size:0.78rem;color:#64748b;'> indexed</span></div>",
            unsafe_allow_html=True,
        )

    if _is_indexed():
        st.markdown("<hr class='mp-hr'>", unsafe_allow_html=True)
        st.markdown("**Indexed files**")
        for f in st.session_state.indexed_files:
            st.markdown(f"- `{f}`")


# ── Page: System ──────────────────────────────────────────────────────────────
def _page_system():
    st.markdown(
        "<div class='section-header'>⚙️ System</div>"
        "<div class='section-sub'>Configuration and diagnostics.</div>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='mp-card'>", unsafe_allow_html=True)
        st.markdown("**LLM Configuration**")
        chat_model = os.getenv("OLLAMA_CHAT_MODEL", "llama3.2") if PROVIDER == "ollama" \
            else os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text") if PROVIDER == "ollama" \
            else "text-embedding-3-small"
        st.code(
            f"LLM_PROVIDER:  {PROVIDER}\n"
            f"Chat model:    {chat_model}\n"
            f"Embed model:   {embed_model}\n"
            f"Vector store:  Chroma  →  {PERSIST_DIR}/\n"
            f"TOP_K:         4",
            language="text",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='mp-card'>", unsafe_allow_html=True)
        st.markdown("**Runtime**")
        st.code(
            f"Python:   {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}\n"
            f"App:      G1Saathi v{APP_VERSION}\n"
            f"Log dir:  {_LOG_DIR.resolve()}\n"
            f"Index:    {'✅ present' if os.path.isdir(PERSIST_DIR) else '❌ not built'}",
            language="text",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr class='mp-hr'>", unsafe_allow_html=True)

    if st.button("🗑️ Clear Conversation", key="btn_clear_chat"):
        st.session_state.messages = []
        st.session_state.last_sources = []
        st.success("Conversation cleared.")
        st.rerun()

    if PROVIDER == "ollama":
        st.info(
            "**Using Ollama (local)**\n\n"
            "Ensure Ollama is running: `ollama serve`\n\n"
            f"Models needed: `{os.getenv('OLLAMA_CHAT_MODEL','llama3.2')}` "
            f"and `{os.getenv('OLLAMA_EMBED_MODEL','nomic-embed-text')}`\n\n"
            "Pull them if needed:\n"
            "```bash\n"
            f"ollama pull {os.getenv('OLLAMA_CHAT_MODEL','llama3.2')}\n"
            f"ollama pull {os.getenv('OLLAMA_EMBED_MODEL','nomic-embed-text')}\n"
            "```"
        )
    else:
        has_key = bool(os.getenv("OPENAI_API_KEY", ""))
        if has_key:
            st.success("✅ OPENAI_API_KEY is set.")
        else:
            st.error("❌ OPENAI_API_KEY is not set. Add it to your `.env` file.")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    _render_sidebar()

    page = st.session_state.active_page
    if page == "ask":
        _page_ask()
    elif page == "reports":
        _page_reports()
    elif page == "sources":
        _page_sources()
    elif page == "system":
        _page_system()


if __name__ == "__main__":
    main()
