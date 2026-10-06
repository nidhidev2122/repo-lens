"""Pydantic models for request and response validation."""

from typing import Dict, List
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    repo_url: str = Field(..., examples=["https://github.com/octocat/Hello-World"])


class FileInfo(BaseModel):
    path: str
    size: int
    ext: str


class AnalyzeResponse(BaseModel):
    repo_id: str
    repo_name: str
    files_found: int
    languages: Dict[str, int]
    files: List[FileInfo]


class RepoIdRequest(BaseModel):
    repo_id: str


class ExplainResponse(BaseModel):
    explanation: str


class FlowchartResponse(BaseModel):
    mermaid: str
    source: str = Field(..., description="'llm' or 'fallback'")


class HealthResponse(BaseModel):
    backend: bool
    ollama: bool
    model_ready: bool
    model: str
