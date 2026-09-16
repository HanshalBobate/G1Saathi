# Phase 3 RAG Evaluation Suite

This evaluation suite assesses the **Evidence Quality & RAG Reliability** of the G1Saathi Agentic AI Healthcare Assistant.

## What is tested
- **Local KB Retrieval**: Testing basic facts present in the local database.
- **Current Info Routing**: Testing questions about 2026 guidelines or recent medical events to ensure it routes to the `ExternalResearchAgent`.
- **Emergency Safety Gate**: Testing questions about heart attacks, suicide, and strokes to ensure they are immediately blocked with a `HIGH` risk level.
- **Fictional Entity Rejection**: Testing completely made-up diseases to ensure the system correctly identifies `INSUFFICIENT` evidence and refuses to answer, rather than hallucinating.

## Running the Suite

Ensure `llama3.2` and `nomic-embed-text` are running via Ollama.

```bash
python evaluation/run_evaluation.py
```

Results will be printed to stdout and saved to `evaluation/report.json`.
