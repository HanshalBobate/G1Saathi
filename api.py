"""FastAPI service exposing the medical RAG pipeline.

The same ingest / retrieval core powers both the Streamlit app (app.py) and this
HTTP API, so any frontend (or another service) can consume it.

Run:
    uvicorn api:app --reload
Interactive docs:
    http://localhost:8000/docs

Endpoints:
    GET    /health          liveness check
    GET    /status          whether an index exists + which files
    POST   /index           upload PDFs (multipart) and (re)build the index
    POST   /ask             ask a question -> grounded, cited answer
    DELETE /index           clear the index
"""

import os
import shutil
from typing import List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ingest import clear_index, ingest
from models import PROVIDER
from agents.orchestrator import run_orchestrator

UPLOAD_DIR = "data/uploads"
PERSIST_DIR = "chroma_db"

app = FastAPI(
    title="G1Saathi Healthcare API",
    version="1.0.0",
    description="Grounded, cited question answering over your medical PDFs.",
)

# Allow browser frontends to call the API. Tighten allow_origins for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-process record of what is indexed (fine for a single-worker demo).
STATE = {"indexed_files": []}


# ---------- schemas ----------
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, examples=["What are the reported accuracy results?"])
    context: List[dict] = Field(default_factory=list, description="Conversation history context")


class Source(BaseModel):
    file: str
    page: int
    score: Optional[float] = None
    excerpt: str


class AskResponse(BaseModel):
    answer: str
    sources: List[Source]
    agent_trace: List[str] = Field(default_factory=list)
    risk_level: str = "LOW"
    safety_alert: Optional[str] = None


class IndexResponse(BaseModel):
    indexed_files: List[str]
    n_chunks: int
    warnings: List[str] = Field(default_factory=list, description="PDFs with no extractable text (need OCR)")


class StatusResponse(BaseModel):
    indexed: bool
    indexed_files: List[str]
    provider: str


# ---------- routes ----------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/status", response_model=StatusResponse)
def status():
    return StatusResponse(
        indexed=bool(STATE["indexed_files"]) and os.path.isdir(PERSIST_DIR),
        indexed_files=STATE["indexed_files"],
        provider=PROVIDER,
    )


@app.post("/index", response_model=IndexResponse)
async def index(files: List[UploadFile] = File(...)):
    pdfs = [f for f in files if (f.filename or "").lower().endswith(".pdf")]
    if not pdfs:
        raise HTTPException(status_code=400, detail="Upload at least one PDF file.")

    # Clean upload dir so only the current files are indexed.
    shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    paths = []
    for f in pdfs:
        path = os.path.join(UPLOAD_DIR, os.path.basename(f.filename))
        with open(path, "wb") as out:
            out.write(await f.read())
        paths.append(path)

    n_chunks, warnings = ingest(paths, PERSIST_DIR, reset=True)
    STATE["indexed_files"] = [os.path.basename(p) for p in paths]
    return IndexResponse(indexed_files=STATE["indexed_files"], n_chunks=n_chunks, warnings=warnings)


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")
    
    agent_state = run_orchestrator(
        query=req.question,
        conversation_context=req.context,
        persist_dir=PERSIST_DIR
    )
    
    raw_sources = agent_state.citations
    formatted_sources = []
    seen = set()
    for s in raw_sources:
        source_file = s.get("file", "Medical Document")
        page_num = s.get("page", 1)
        snippet = s.get("excerpt", "")
        
        key = (source_file, page_num)
        if key not in seen:
            seen.add(key)
            formatted_sources.append({
                "file": source_file,
                "page": page_num,
                "excerpt": snippet,
            })
            
    emergency_alert = agent_state.final_response if agent_state.risk_level == "HIGH" else None
    
    return AskResponse(
        answer=agent_state.final_response or "",
        sources=formatted_sources,
        agent_trace=agent_state.agent_trace,
        risk_level=agent_state.risk_level,
        safety_alert=emergency_alert
    )


@app.delete("/index")
def clear():
    clear_index(PERSIST_DIR)
    shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
    STATE["indexed_files"] = []
    return {"cleared": True}
