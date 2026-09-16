"""
G1Saathi — Flask Web Application
Agentic AI Healthcare Information Assistant
Wraps the Medical-RAG core with:
  - Production Flask REST backend
  - Safety screening (emergency/crisis detection)
  - Medical report PDF ingestion & indexing
  - Real-time page-level citations
  - Structured rotating-file logging
  - Modern bespoke dark healthcare UI

Run:
    python app.py
Access:
    http://127.0.0.1:5000
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request
from pypdf import PdfReader
from werkzeug.utils import secure_filename

# ── Structured Logging ────────────────────────────────────────────────────────
from logging_config import setup_logging

_LOG_DIR = Path("logs")
setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"), log_dir=_LOG_DIR)
logger = logging.getLogger(__name__)
logger.info("G1Saathi Flask starting up (Python %s.%s)", sys.version_info.major, sys.version_info.minor)

# ── Upstream Core ─────────────────────────────────────────────────────────────
from ingest import clear_index, ingest
from models import PROVIDER
from agents.orchestrator import run_orchestrator

# ── App Configuration ─────────────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "g1saathi-healthcare-secure-key-2026")
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64 MB upload ceiling

UPLOAD_DIR = Path("data/uploads")
PERSIST_DIR = Path("chroma_db")
EXAMPLES_DIR = Path("examples")
TOKEN_REGISTRY_PATH = Path("data/tokens.json")
APP_VERSION = "1.0.0"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_chroma_indexed_documents() -> list[dict[str, Any]]:
    """Query Chroma directly to get all actually indexed files and chunk counts."""
    if not PERSIST_DIR.is_dir():
        return []
    try:
        from rag_chain import get_vectorstore
        store = get_vectorstore(str(PERSIST_DIR))
        col = store._collection
        count = col.count()
        if count == 0:
            return []
        data = col.get()
        metadatas = data.get("metadatas") or []
        doc_stats = {}
        for m in metadatas:
            src = m.get("source") or "Medical Document"
            name = os.path.basename(src)
            page = m.get("page", 0) + 1
            if name not in doc_stats:
                doc_stats[name] = {"name": name, "chunks": 0, "pages": set()}
            doc_stats[name]["chunks"] += 1
            doc_stats[name]["pages"].add(page)

        return [
            {
                "name": name,
                "chunks": info["chunks"],
                "page_count": len(info["pages"]),
                "status": "Indexed",
            }
            for name, info in sorted(doc_stats.items())
        ]
    except Exception as exc:
        logger.warning("Could not query Chroma collection: %s", exc)
        return []


def _is_indexed() -> bool:
    """Returns True if Chroma persistent directory contains any indexed chunks."""
    docs = get_chroma_indexed_documents()
    return len(docs) > 0


def _load_tokens() -> dict[str, dict[str, Any]]:
    """Loads persistent cryptographic token registry for uploaded PDFs."""
    if TOKEN_REGISTRY_PATH.is_file():
        try:
            with open(TOKEN_REGISTRY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_tokens(tokens: dict[str, dict[str, Any]]) -> None:
    """Saves cryptographic token registry to disk."""
    TOKEN_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(TOKEN_REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(tokens, f, indent=2)
    except Exception as exc:
        logger.warning("Could not persist tokens: %s", exc)


def compute_pdf_crypt_token(pdf_bytes: bytes) -> str:
    """
    Generate a cryptic token from PDF text content to guarantee no PDF is uploaded twice,
    even under different filenames. Follows the requested XOR hashing logic:
        crypt = None
        for i in range(0, pdf.text.len, 100):
            crypt ^= pdf.text[i]
    Combined with content hash for guaranteed uniqueness.
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        extracted_pages = [page.extract_text() or "" for page in reader.pages]
        text = "".join(extracted_pages)
    except Exception as exc:
        logger.warning("Failed to extract text from PDF: %s", exc)
        text = ""

    clean_text = "".join(text.split())
    if not clean_text:
        # Fallback for scanned/empty PDFs: hash raw payload
        return "CRYPT-RAW-" + hashlib.sha256(pdf_bytes).hexdigest()[:16].upper()

    crypt = 0
    for i in range(0, len(clean_text), 100):
        char_val = ord(clean_text[i])
        crypt = ((crypt << 5) - crypt) ^ char_val
        crypt &= 0xFFFFFFFF

    content_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()[:16]
    return f"CRYPT-{crypt:08X}-{content_hash}"


def _get_uploaded_files() -> list[dict[str, Any]]:
    """Returns metadata (including cryptic content token) for all PDFs currently in UPLOAD_DIR."""
    if not UPLOAD_DIR.is_dir():
        return []
    tokens = _load_tokens()
    files = []
    tokens_modified = False

    for p in sorted(UPLOAD_DIR.iterdir()):
        if p.is_file() and p.suffix.lower() == ".pdf":
            file_token = tokens.get(p.name, {}).get("token")
            if not file_token:
                try:
                    with open(p, "rb") as f:
                        file_token = compute_pdf_crypt_token(f.read())
                    tokens[p.name] = {
                        "token": file_token,
                        "size_kb": round(p.stat().st_size / 1024, 1),
                    }
                    tokens_modified = True
                except Exception:
                    file_token = "N/A"

            files.append({
                "name": p.name,
                "size_kb": round(p.stat().st_size / 1024, 1),
                "modified": int(p.stat().st_mtime),
                "token": file_token,
            })

    if tokens_modified:
        _save_tokens(tokens)

    return files


def _get_example_files() -> list[dict[str, Any]]:
    """Returns available sample papers in examples/."""
    if not EXAMPLES_DIR.is_dir():
        return []
    examples = []
    for p in sorted(EXAMPLES_DIR.iterdir()):
        if p.is_file() and p.suffix.lower() == ".pdf":
            examples.append({
                "name": p.name,
                "size_kb": round(p.stat().st_size / 1024, 1),
            })
    return examples


# ── Page Routes ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    """Render the primary single-page application dashboard."""
    return render_template(
        "index.html",
        app_name="G1Saathi",
        app_version=APP_VERSION,
        provider=PROVIDER.upper(),
        is_indexed=_is_indexed(),
    )


# ── API: Status & State ───────────────────────────────────────────────────────
@app.route("/api/status", methods=["GET"])
def api_status():
    """Returns real vector store state, indexed documents from Chroma, and queue info."""
    chat_model = (
        os.getenv("OLLAMA_CHAT_MODEL", "llama3.2")
        if PROVIDER == "ollama"
        else "gpt-4o-mini"
    )
    embed_model = (
        os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        if PROVIDER == "ollama"
        else "text-embedding-3-small"
    )
    indexed_docs = get_chroma_indexed_documents()
    total_chunks = sum(d["chunks"] for d in indexed_docs)
    is_indexed = total_chunks > 0
    uploaded_files = _get_uploaded_files()

    import time
    from datetime import datetime
    
    last_indexed = None
    db_path = PERSIST_DIR / "chroma.sqlite3"
    if db_path.exists():
        mtime = db_path.stat().st_mtime
        last_indexed = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

    return jsonify({
        "app_name": "G1Saathi",
        "version": APP_VERSION,
        "provider": PROVIDER,
        "chat_model": chat_model,
        "embed_model": embed_model,
        "is_indexed": is_indexed,
        "total_chunks": total_chunks,
        "indexed_documents": indexed_docs,
        "indexed_count": len(indexed_docs),
        "files": uploaded_files,
        "file_count": len(uploaded_files),
        "persist_dir": str(PERSIST_DIR.resolve()),
        "last_indexed": last_indexed
    })


# ── Workflow Telemetry ──────────────────────────────────────────────────────────
METRICS_FILE = Path("data/metrics.json")

def _load_metrics() -> dict[str, Any]:
    if METRICS_FILE.is_file():
        try:
            with open(METRICS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {
        "queries": 0,
        "total_llm_calls": 0,
        "total_vector_searches": 0,
        "external_research_queries": 0,
        "emergency_interceptions": 0,
        "grounding_revisions": 0,
        "insufficient_evidence_responses": 0
    }

def _save_metrics(metrics: dict[str, Any]):
    METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(metrics, f)

@app.route("/api/workflow/metrics", methods=["GET"])
def api_workflow_metrics():
    m = _load_metrics()
    q = max(1, m["queries"])
    return jsonify({
        "queries": m["queries"],
        "avg_llm_calls": round(m["total_llm_calls"] / q, 1),
        "avg_vector_searches": round(m["total_vector_searches"] / q, 1),
        "external_research_queries": m["external_research_queries"],
        "emergency_interceptions": m["emergency_interceptions"],
        "insufficient_evidence_responses": m.get("insufficient_evidence_responses", 0),
        "grounding_revisions": m["grounding_revisions"]
    })


# ── API: Ask & RAG Chain ──────────────────────────────────────────────────────
@app.route("/api/ask", methods=["POST"])
def api_ask():
    """Receives query, checks safety emergency criteria, executes grounded RAG via Agentic Orchestrator."""
    data = request.get_json(force=True, silent=True) or {}
    question = (data.get("question") or data.get("query") or "").strip()
    context = data.get("context") or []
    mode = data.get("mode") or "ask"
    files = data.get("files") or []

    if not question and mode not in ["analyze", "compare"]:
        return jsonify({"error": "A question is required."}), 400

    logger.info("Query received (mode=%s): %s...", mode, question[:60])

    # 1. Check index availability
    if not _is_indexed() and not files:
        return jsonify({
            "answer": "No medical documents are indexed yet.",
            "sources": [],
            "safety_alert": None,
            "is_indexed": False,
        })

    # 2. Run Orchestrator Workflow
    try:
        agent_state = run_orchestrator(
            query=question,
            conversation_context=context,
            persist_dir=str(PERSIST_DIR),
            mode=mode,
            files=files
        )
        
        # 3. Update runtime metrics
        m = _load_metrics()
        m["queries"] += 1
        tc = getattr(agent_state, "tool_calls", {})
        
        m["total_llm_calls"] += sum(v for k, v in tc.items() if k.startswith("llm_"))
        m["total_vector_searches"] += tc.get("chroma_search", 0)
        m["external_research_queries"] += tc.get("external_search", 0)
        
        if agent_state.risk_level == "HIGH":
            m["emergency_interceptions"] += 1
        if agent_state.evidence_status == "INSUFFICIENT":
            m["insufficient_evidence_responses"] = m.get("insufficient_evidence_responses", 0) + 1
        if "⚠ Unsupported claim detected" in agent_state.agent_trace:
            m["grounding_revisions"] += 1
            
        _save_metrics(m)

        answer_text = agent_state.final_response or ""
        raw_sources = agent_state.citations
        
        formatted_sources = []
        seen = set()
        for s in raw_sources:
            if "domain" in s:
                key = s.get("url")
                if key not in seen:
                    seen.add(key)
                    formatted_sources.append({
                        "type": "external",
                        "domain": s.get("domain", ""),
                        "title": s.get("title", ""),
                        "url": key,
                        "snippet": s.get("snippet", ""),
                        "retrieved_at": s.get("retrieved_at", "")
                    })
            else:
                source_file = s.get("file", "Medical Document")
                page_num = s.get("page", 1)
                snippet = s.get("excerpt", "")
                
                key = (source_file, page_num)
                if key not in seen:
                    seen.add(key)
                    formatted_sources.append({
                        "type": "local",
                        "file": source_file,
                        "page": page_num,
                        "snippet": snippet,
                        "score": s.get("score")
                    })

        emergency_alert = agent_state.final_response if agent_state.risk_level == "HIGH" else None

        # Build task plan representation for UI
        tp_dict = None
        if hasattr(agent_state, "task_plan") and agent_state.task_plan:
            tp_dict = {
                "task_type": agent_state.task_plan.task_type.value,
                "steps": agent_state.task_plan.steps
            }

        return jsonify({
            "answer": answer_text,
            "sources": formatted_sources,
            "safety_alert": emergency_alert,
            "is_indexed": True,
            "agent_trace": agent_state.agent_trace,
            "risk_level": agent_state.risk_level,
            "evidence_quality_metrics": agent_state.evidence_quality_metrics,
            "extracted_claims": agent_state.extracted_claims,
            "retrieval_diagnostics": agent_state.retrieval_diagnostics,
            "language": agent_state.language,
            "entities": agent_state.entities,
            "next_steps": getattr(agent_state, "next_steps", []),
            "task_plan": tp_dict,
            "tool_calls": tc,
            "information_gap": getattr(agent_state, "information_gap", None)
        })

    except Exception as exc:
        logger.exception("Error executing Agent Workflow: %s", exc)
        return jsonify({
            "error": f"Failed to generate answer: {str(exc)}",
            "safety_alert": None,
        }), 500


# ── API: File Uploads ─────────────────────────────────────────────────────────
@app.route("/api/upload", methods=["POST"])
def api_upload():
    """
    Uploads one or more PDF files into data/uploads/.
    Calculates a cryptic token for each PDF based on text sampling and rejects
    any duplicate document even if uploaded under a different filename.
    """
    if "files" not in request.files:
        return jsonify({"error": "No files part in request."}), 400

    uploaded_files = request.files.getlist("files")
    saved = []
    rejected = []
    tokens = _load_tokens()
    existing_files = _get_uploaded_files()

    # Map all previously indexed or uploaded tokens -> filename
    existing_token_map = {
        meta["token"]: fname
        for fname, meta in tokens.items()
        if isinstance(meta, dict) and meta.get("token") and meta["token"] != "N/A"
    }
    for f in existing_files:
        if f.get("token") and f["token"] != "N/A":
            existing_token_map[f["token"]] = f["name"]

    for f in uploaded_files:
        if not f.filename:
            continue
        filename = secure_filename(f.filename)
        if not filename.lower().endswith(".pdf"):
            rejected.append({"name": filename, "reason": "Not a PDF file.", "token": None})
            continue

        file_bytes = f.read()
        token = compute_pdf_crypt_token(file_bytes)

        # Content duplicate check
        if token in existing_token_map:
            matched_file = existing_token_map[token]
            logger.warning("Duplicate PDF rejected: '%s' matches '%s' (Token: %s)", filename, matched_file, token)
            rejected.append({
                "name": filename,
                "reason": f"Duplicate document: identical content to already uploaded '{matched_file}'",
                "token": token,
                "matched_with": matched_file,
            })
            continue

        target_path = UPLOAD_DIR / filename
        with open(target_path, "wb") as out:
            out.write(file_bytes)

        size_kb = round(len(file_bytes) / 1024, 1)
        tokens[filename] = {
            "token": token,
            "size_kb": size_kb,
        }
        existing_token_map[token] = filename

        saved.append({
            "name": filename,
            "size_kb": size_kb,
            "token": token,
        })

    _save_tokens(tokens)
    logger.info("Upload complete — saved %d, rejected %d", len(saved), len(rejected))
    return jsonify({
        "saved": saved,
        "rejected": rejected,
        "all_files": _get_uploaded_files(),
    })


# ── API: Delete File from Queue ───────────────────────────────────────────────
@app.route("/api/delete-file", methods=["POST"])
def api_delete_file():
    """Removes a single PDF file from the upload queue and updates tokens."""
    data = request.get_json(force=True, silent=True) or {}
    filename = secure_filename(data.get("filename") or "")
    if not filename:
        return jsonify({"error": "Filename is required"}), 400

    target = UPLOAD_DIR / filename
    if target.is_file():
        target.unlink(missing_ok=True)
        tokens = _load_tokens()
        tokens.pop(filename, None)
        _save_tokens(tokens)
        logger.info("Removed %s from uploads queue", filename)

    return jsonify({
        "success": True,
        "message": f"Removed '{filename}' from queue.",
        "all_files": _get_uploaded_files(),
    })


# ── API: Clear Entire Queue ───────────────────────────────────────────────────
@app.route("/api/clear-queue", methods=["POST"])
def api_clear_queue():
    """Removes all PDF files from data/uploads/ queue."""
    for p in UPLOAD_DIR.glob("*"):
        if p.is_file():
            p.unlink(missing_ok=True)
    if TOKEN_REGISTRY_PATH.is_file():
        TOKEN_REGISTRY_PATH.unlink(missing_ok=True)
    logger.info("Cleared all files from upload queue")
    return jsonify({
        "success": True,
        "message": "All reports have been removed from the queue.",
        "all_files": _get_uploaded_files(),
    })


# ── API: Load Example Samples ─────────────────────────────────────────────────
@app.route("/api/load-samples", methods=["POST"])
def api_load_samples():
    """Copies synthetic sample PDFs from examples/ into data/uploads/."""
    if not EXAMPLES_DIR.is_dir():
        return jsonify({"error": "Examples directory not found."}), 404

    tokens = _load_tokens()
    existing_files = _get_uploaded_files()
    existing_token_map = {
        meta["token"]: fname
        for fname, meta in tokens.items()
        if isinstance(meta, dict) and meta.get("token") and meta["token"] != "N/A"
    }
    for f in existing_files:
        if f.get("token") and f["token"] != "N/A":
            existing_token_map[f["token"]] = f["name"]
    copied = []
    skipped = []

    for p in EXAMPLES_DIR.glob("*.pdf"):
        with open(p, "rb") as f:
            b = f.read()
        token = compute_pdf_crypt_token(b)
        if token in existing_token_map:
            skipped.append(p.name)
            continue

        dest = UPLOAD_DIR / p.name
        with open(dest, "wb") as f:
            f.write(b)

        tokens[p.name] = {
            "token": token,
            "size_kb": round(p.stat().st_size / 1024, 1),
        }
        existing_token_map[token] = p.name
        copied.append(p.name)

    _save_tokens(tokens)

    logger.info("Loaded %d sample files into uploads (%d skipped duplicates)", len(copied), len(skipped))
    msg = f"Loaded {len(copied)} sample document(s)."
    if skipped:
        msg += f" ({len(skipped)} already loaded/duplicate)."
    return jsonify({
        "message": msg,
        "loaded": copied,
        "skipped": skipped,
        "all_files": _get_uploaded_files(),
    })


# ── API: Ingest / Index ───────────────────────────────────────────────────────
@app.route("/api/index", methods=["POST"])
def api_index():
    """Indexes all PDFs currently located in data/uploads/ into Chroma vector store."""
    files = _get_uploaded_files()
    if not files:
        return jsonify({"error": "No PDF files in upload directory to index."}), 400

    logger.info("Starting ingestion of %d PDF(s)...", len(files))
    try:
        num_chunks, warnings = ingest(
            source=str(UPLOAD_DIR),
            persist_dir=str(PERSIST_DIR),
            reset=True,
        )
        file_names = [f["name"] for f in files]
        logger.info(
            "Ingestion completed: chunks=%d, files=%d, warnings=%s",
            num_chunks,
            len(file_names),
            warnings,
        )
        return jsonify({
            "success": True,
            "num_chunks": num_chunks,
            "files": file_names,
            "scanned_files": warnings,
        })
    except Exception as exc:
        logger.exception("Ingest failed: %s", exc)
        return jsonify({"error": f"Ingestion failed: {str(exc)}"}), 500


# ── API: Clear Index ──────────────────────────────────────────────────────────
@app.route("/api/clear", methods=["POST"])
def api_clear():
    """Clears Chroma vector store and removes uploaded documents."""
    logger.info("Clearing vector index and upload cache...")
    try:
        clear_index(str(PERSIST_DIR))

        # Clear files in UPLOAD_DIR
        for p in UPLOAD_DIR.glob("*"):
            if p.is_file():
                p.unlink(missing_ok=True)

        if TOKEN_REGISTRY_PATH.is_file():
            TOKEN_REGISTRY_PATH.unlink(missing_ok=True)

        logger.info("Index and uploads cleared successfully.")
        return jsonify({
            "success": True,
            "message": "Vector store and uploaded files have been cleared.",
        })
    except Exception as exc:
        logger.exception("Error clearing index: %s", exc)
        return jsonify({"error": f"Failed to clear index: {str(exc)}"}), 500


# ── API: System Diagnostics ───────────────────────────────────────────────────
@app.route("/api/system", methods=["GET"])
def api_system():
    """Provides detailed runtime configuration and diagnostics."""
    log_file = _LOG_DIR / "g1saathi.log"
    log_size_kb = round(log_file.stat().st_size / 1024, 1) if log_file.exists() else 0.0

    return jsonify({
        "app_name": "G1Saathi",
        "app_version": APP_VERSION,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "provider": PROVIDER,
        "chat_model": os.getenv("OLLAMA_CHAT_MODEL", "llama3.2") if PROVIDER == "ollama" else "gpt-4o-mini",
        "embed_model": os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text") if PROVIDER == "ollama" else "text-embedding-3-small",
        "log_dir": str(_LOG_DIR.resolve()),
        "log_file_size_kb": log_size_kb,
        "persist_dir": str(PERSIST_DIR.resolve()),
        "is_indexed": _is_indexed(),
        "total_uploaded_files": len(_get_uploaded_files()),
    })


# ── API: Evaluation & Reliability Center ──────────────────────────────────────
@app.route("/api/evaluation/results", methods=["GET"])
def api_eval_results():
    """Returns the latest evaluation suite results."""
    eval_file = Path("evaluation/results/latest.json")
    if eval_file.is_file():
        try:
            with open(eval_file, "r", encoding="utf-8") as f:
                return jsonify(json.load(f))
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "No evaluation results found"}), 404

@app.route("/api/evaluation/history", methods=["GET"])
def api_eval_history():
    """Returns historical evaluation runs."""
    results_dir = Path("evaluation/results")
    if not results_dir.is_dir():
        return jsonify({"history": []})
    
    history = []
    for p in results_dir.glob("*.json"):
        if p.name != "latest.json":
            history.append(p.name)
    return jsonify({"history": sorted(history, reverse=True)})

@app.route("/api/evaluation/run", methods=["POST"])
def api_eval_run():
    """Triggers the evaluation suite runner asynchronously."""
    import subprocess
    import threading
    
    def run_eval():
        # Set PYTHONPATH so the script can import agents
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).parent.resolve())
        subprocess.run([sys.executable, "evaluation/run_evaluation.py"], env=env, cwd=str(Path(__file__).parent.resolve()))
        
    thread = threading.Thread(target=run_eval)
    thread.start()
    
    return jsonify({"status": "Evaluation started in background"})

@app.route("/api/evaluation/export/csv", methods=["GET"])
def api_eval_export_csv():
    """Exports the latest evaluation results as CSV."""
    import io
    import csv
    from flask import Response
    
    eval_file = Path("evaluation/results/latest.json")
    if not eval_file.is_file():
        return jsonify({"error": "No evaluation results found"}), 404
        
    try:
        with open(eval_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "category", "query", "passed", "evidence_status",
            "evidence_coverage", "claims_supported", "external_research",
            "emergency", "llm_calls", "vector_searches", "reason"
        ])
        
        for r in data.get("results", []):
            writer.writerow([
                r.get("question_id"),
                r.get("category"),
                r.get("query"),
                r.get("passed"),
                r.get("actual_status"),
                r.get("evidence_coverage"),
                r.get("claims_supported"),
                r.get("external_research_used"),
                r.get("emergency_triggered"),
                r.get("llm_calls"),
                r.get("vector_searches"),
                r.get("reason")
            ])
            
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=evaluation_results.csv"}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── API: Medical Ontology ─────────────────────────────────────────────────────
@app.route("/api/analyze-report", methods=["POST"])
def api_analyze_report():
    """Parses a specific uploaded PDF directly to extract structured measurements."""
    data = request.get_json(force=True, silent=True) or {}
    filename = secure_filename(data.get("filename") or "")
    if not filename:
        return jsonify({"error": "Filename is required"}), 400

    target = UPLOAD_DIR / filename
    if not target.is_file():
        return jsonify({"error": f"File {filename} not found."}), 404

    from document_analysis.document_text import extract_pdf_pages
    from document_analysis.report_parser import parse_medical_report
    
    try:
        pages = extract_pdf_pages(str(target))
        measurements = parse_medical_report(pages)
        return jsonify({
            "document": filename,
            "measurements": measurements
        })
    except Exception as e:
        logger.exception("Report analysis failed: %s", e)
        return jsonify({"error": f"Analysis failed: {e}"}), 500

@app.route("/api/compare-reports", methods=["POST"])
def api_compare_reports():
    """Compares two PDF reports and calculates numerical trends."""
    data = request.get_json(force=True, silent=True) or {}
    files = data.get("filenames", [])
    if len(files) != 2:
        return jsonify({"error": "Exactly two filenames are required for comparison"}), 400
        
    f1, f2 = secure_filename(files[0]), secure_filename(files[1])
    t1, t2 = UPLOAD_DIR / f1, UPLOAD_DIR / f2
    
    if not t1.is_file() or not t2.is_file():
        return jsonify({"error": "One or both files not found in uploads."}), 404
        
    from document_analysis.document_text import extract_pdf_pages
    from document_analysis.report_parser import parse_medical_report
    from document_analysis.report_comparator import compare_reports
    
    try:
        pages1 = extract_pdf_pages(str(t1))
        meas1 = parse_medical_report(pages1)
        
        pages2 = extract_pdf_pages(str(t2))
        meas2 = parse_medical_report(pages2)
        
        # In a real app we'd sort by parsed report_date. For now we assume f1 is older, f2 is newer as passed by UI.
        trends = compare_reports(meas1, meas2)
        
        return jsonify({
            "reports": [f1, f2],
            "trends": trends
        })
    except Exception as e:
        logger.exception("Report comparison failed: %s", e)
        return jsonify({"error": f"Comparison failed: {e}"}), 500


@app.route("/api/ontology", methods=["GET"])
def api_ontology():
    """Returns the loaded medical ontology for the frontend UI."""
    ontology_path = Path("knowledge/medical_ontology.json")
    if ontology_path.exists():
        try:
            with open(ontology_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return jsonify({"entities": data})
        except Exception as e:
            return jsonify({"error": f"Failed to load ontology: {e}"}), 500
    return jsonify({"entities": []})

# ── API: 3D Vector Database Representation ────────────────────────────────────
@app.route("/api/embeddings/3d", methods=["GET"])
def api_embeddings_3d():
    """Fetches embeddings from ChromaDB, reduces to 3D via PCA, and returns for plotting."""
    if not _is_indexed():
        return jsonify({"error": "No documents indexed"}), 400
        
    try:
        from rag_chain import get_vectorstore
        store = get_vectorstore(str(PERSIST_DIR))
        col = store._collection
        data = col.get(include=["embeddings", "metadatas", "documents"])
        
        embeddings = data.get("embeddings")
        if embeddings is None or len(embeddings) == 0:
            return jsonify({"error": "No embeddings found"}), 404
            
        import numpy as np
        from sklearn.decomposition import PCA
        
        # We need at least 3 samples to do 3D PCA. If less, pad with zeros conceptually, 
        # or just set n_components dynamically and pad the rest.
        n_components = min(3, len(embeddings))
        pca = PCA(n_components=n_components)
        reduced = pca.fit_transform(embeddings)
        
        # If we had fewer than 3 dimensions (e.g. 1 or 2 chunks), pad the output to 3D
        if reduced.shape[1] < 3:
            padding = np.zeros((reduced.shape[0], 3 - reduced.shape[1]))
            reduced = np.hstack((reduced, padding))
            
        points = []
        metadatas = data.get("metadatas") or []
        documents = data.get("documents") or []
        tokens = _load_tokens()
        
        for i in range(len(reduced)):
            meta = metadatas[i] if i < len(metadatas) else {}
            doc_text = documents[i] if i < len(documents) else ""
            source_file = os.path.basename(meta.get("source", "Unknown"))
            file_token = tokens.get(source_file, {}).get("token", "default")
            
            points.append({
                "x": float(reduced[i][0]),
                "y": float(reduced[i][1]),
                "z": float(reduced[i][2]),
                "source": source_file,
                "page": meta.get("page", 0) + 1,
                "text": doc_text[:200] + ("..." if len(doc_text) > 200 else ""),
                "token": file_token
            })
            
        return jsonify({"points": points})
        
    except ImportError:
        logger.error("scikit-learn not installed.")
        return jsonify({"error": "Server missing dependency: scikit-learn"}), 500
    except Exception as exc:
        logger.exception("Error generating 3D embeddings: %s", exc)
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "127.0.0.1")
    logger.info("Starting G1Saathi Flask web server at http://%s:%d", host, port)
    app.run(host=host, port=port, debug=True)
