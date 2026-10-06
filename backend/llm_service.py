"""Talk to Ollama and generate beginner-friendly repository explanations."""

import os
import re
from typing import Dict, List, Optional, Tuple

import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")


def ollama_status() -> Tuple[bool, bool]:
    try:
        tags = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2).json()
        names = [m["name"] for m in tags.get("models", [])]
        return True, any(n.startswith(MODEL.split(":")[0]) for n in names)
    except Exception:
        return False, False


def ask_llm(prompt: str) -> str:
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            timeout=600,
            json={"model": MODEL, "prompt": prompt, "stream": False,
                  "options": {"num_ctx": 8192, "temperature": 0.25}},
        )
        response.raise_for_status()
        return response.json()["response"].strip()
    except Exception as err:
        raise RuntimeError(f"Is Ollama running with '{MODEL}' pulled? ({err})") from err


def explain_repo(name: str, tree: str, code: str) -> str:
    prompt = f"""You explain GitHub repositories to someone who says: 'I don't understand this code.'
Be concrete, beginner-friendly, and only use facts visible in the repository.
Repository: {name}

File tree:
{tree[:3000]}

Important code:
{code}

Return EXACTLY these four headings and nothing else:
Project Overview
2-4 short sentences explaining what the project is, who/what uses it, and its main purpose.

The application allows users to:
- 3-6 concise bullets describing the important user-facing actions or capabilities.

Main Technologies:
- List only technologies/frameworks/libraries you can verify from the files.

How it works:
1. Explain the input/entry point.
2. Explain the important processing steps.
3. Explain the AI/backend/storage/output path.
4. Mention important boundaries or limitations if visible.

Do not invent features, APIs, databases, or deployment details."""
    return ask_llm(prompt)


def make_flowchart(name: str, tree: str, code: str, files: List[Dict]) -> Tuple[str, str]:
    prompt = f"""Create a clean Mermaid flowchart for the repository '{name}'.
The goal is instant understanding, not technical decoration.

Files:
{tree[:2500]}

Important code:
{code[:8000]}

Rules:
- Output ONLY Mermaid code. No markdown fences. No explanation.
- First line: flowchart TD
- Use 6-14 nodes maximum.
- Use simple node ids: A, B, C, ...
- Every label must be short and beginner-friendly.
- Show a clear top-to-bottom story: user/input -> entry point -> main processing -> AI/services -> result/output.
- Group closely related files into one meaningful node instead of listing every file.
- Include important decision/storage steps only when they are actually present.
- Avoid parentheses, quotes, slashes, emojis, and punctuation inside node labels.
- Use arrows with short relationships where useful, e.g. A -->|sends| B.
- End at a clear user-visible result.
"""
    try:
        chart = _clean_mermaid(ask_llm(prompt))
    except RuntimeError:
        chart = None
    if chart:
        return chart, "llm"
    return _fallback_flowchart(files), "fallback"


def _clean_mermaid(text: str) -> Optional[str]:
    text = re.sub(r"```(?:mermaid)?", "", text, flags=re.IGNORECASE).strip()
    idx = text.lower().find("flowchart")
    if idx == -1:
        return None
    text = text[idx:]
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    chart = "\n".join(lines)
    if len(lines) < 3 or "-->" not in chart or len(chart) > 12000:
        return None
    return chart


def _fallback_flowchart(files: List[Dict]) -> str:
    folders: Dict[str, int] = {}
    for file in files[:80]:
        parts = file["path"].split("/")
        key = parts[0] if len(parts) > 1 else "root"
        folders[key] = folders.get(key, 0) + 1
    lines = ["flowchart TD", "  A[Repository]"]
    previous = "A"
    for index, (folder, count) in enumerate(list(folders.items())[:9], start=1):
        node = chr(64 + index) if index <= 26 else f"N{index}"
        label = re.sub(r"[^A-Za-z0-9 _-]", "", folder)[:24] or "root"
        lines.append(f"  {node}[{label} {count} files]")
        lines.append(f"  {previous} --> {node}")
        previous = node
    return "\n".join(lines)
