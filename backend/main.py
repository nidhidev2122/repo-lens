"""FastAPI backend for RepoLens.

Run from the project root:
    uvicorn backend.main:app --port 8000
"""

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from backend import llm_service as llm
    from backend import repo_processor as rp
    from backend import schemas as sc
except ImportError:
    import llm_service as llm
    import repo_processor as rp
    import schemas as sc

app = FastAPI(
    title="RepoLens API",
    description="Analyze and explain public GitHub repositories with a local LLM.",
    version="2.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

STORE: dict = {}


def _get(repo_id: str) -> dict:
    if repo_id not in STORE:
        raise HTTPException(404, "Repository not analyzed yet. Analyze it first.")
    return STORE[repo_id]


@app.get("/health", response_model=sc.HealthResponse)
def health():
    ollama_up, model_ready = llm.ollama_status()
    return sc.HealthResponse(backend=True, ollama=ollama_up, model_ready=model_ready, model=llm.MODEL)


@app.post("/analyze", response_model=sc.AnalyzeResponse)
def analyze(req: sc.AnalyzeRequest):
    try:
        repo_id, name, path = rp.clone_repo(req.repo_url)
    except (ValueError, RuntimeError) as err:
        raise HTTPException(400, str(err)) from err
    files = rp.scan_files(path)
    if not files:
        raise HTTPException(400, "No source files found in this repository.")
    STORE[repo_id] = {"name": name, "path": path, "files": files}
    languages: dict = {}
    for f in files:
        languages[f["ext"]] = languages.get(f["ext"], 0) + 1
    return sc.AnalyzeResponse(
        repo_id=repo_id, repo_name=name, files_found=len(files), languages=languages, files=files
    )


@app.post("/explain", response_model=sc.ExplainResponse)
def explain(req: sc.RepoIdRequest):
    repo = _get(req.repo_id)
    code = rp.build_context(repo["path"], repo["files"])
    try:
        text = llm.explain_repo(repo["name"], rp.tree_text(repo["files"]), code)
    except RuntimeError as err:
        raise HTTPException(503, f"LLM service error: {err}") from err
    return sc.ExplainResponse(explanation=text)


@app.post("/flowchart", response_model=sc.FlowchartResponse)
def flowchart(req: sc.RepoIdRequest):
    repo = _get(req.repo_id)
    code = rp.build_context(repo["path"], repo["files"])
    chart, source = llm.make_flowchart(repo["name"], rp.tree_text(repo["files"]), code, repo["files"])
    return sc.FlowchartResponse(mermaid=chart, source=source)
