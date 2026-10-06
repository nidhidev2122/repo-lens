"""Clone a GitHub repository, pick relevant source files and build LLM context."""

import re
import shutil
import stat
from pathlib import Path
from typing import Dict, List

from git import Repo

ROOT_DIR = Path(__file__).resolve().parent.parent
WORKDIR = ROOT_DIR / "cloned_repos"
URL_RE = re.compile(r"^https://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")

CODE_EXT = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".c", ".cpp",
            ".h", ".cs", ".rb", ".php", ".html", ".css", ".sql", ".kt", ".swift", ".sh"}
CONFIG_FILES = {"readme", "readme.md", "readme.txt", "readme.rst", "requirements.txt", "package.json", "pyproject.toml",
                "dockerfile", "docker-compose.yml", "pom.xml", "go.mod", "cargo.toml"}
ENTRY_FILES = {"main.py", "app.py", "server.py", "index.js", "server.js", "app.js",
               "index.ts", "main.go", "main.java", "manage.py"}
IGNORE_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build",
               ".idea", ".vscode", "target", "vendor", ".next"}
MAX_FILE_BYTES = 100_000


def _on_rm_error(func, path, _exc):
    """Windows keeps .git files read-only; clear the flag and retry."""
    Path(path).chmod(stat.S_IWRITE)
    func(path)


def parse_url(url: str):
    match = URL_RE.match(url.strip())
    if not match:
        raise ValueError("Enter a URL like https://github.com/username/repository")
    return match.group(1), match.group(2)


def clone_repo(url: str):
    """Shallow-clone the repo. Returns (repo_id, repo_name, local_path)."""
    owner, name = parse_url(url)
    repo_id = f"{owner}__{name}"
    path = WORKDIR / repo_id
    if path.exists():
        shutil.rmtree(path, onerror=_on_rm_error)
    WORKDIR.mkdir(exist_ok=True)
    try:
        Repo.clone_from(f"https://github.com/{owner}/{name}.git", path, depth=1)
    except Exception as err:
        raise RuntimeError(f"Could not clone repository: {err}") from err
    return repo_id, name, path


def _priority(path: Path) -> int:
    name = path.name.lower()
    if name.startswith("readme"):
        return 0
    if name in CONFIG_FILES:
        return 1
    if name in ENTRY_FILES:
        return 2
    return 3


def scan_files(root: Path) -> List[Dict]:
    """Return relevant source/config files, most informative first."""
    files = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in IGNORE_DIRS for part in rel.parts):
            continue
        if p.suffix.lower() in CODE_EXT or p.name.lower() in CONFIG_FILES:
            size = p.stat().st_size
            if size <= MAX_FILE_BYTES:
                files.append({"path": rel.as_posix(), "size": size,
                              "ext": p.suffix.lower() or p.name, "priority": _priority(p)})
    return sorted(files, key=lambda f: (f["priority"], f["size"]))


def read_file(root: Path, rel: str) -> str:
    target = (root / rel).resolve()
    if root.resolve() not in target.parents:
        raise ValueError("Invalid path")
    return target.read_text(encoding="utf-8", errors="ignore")


def build_context(root: Path, files: List[Dict], budget=12000, per_file=1500) -> str:
    """Pack the most informative files into a prompt-sized string."""
    out, used = [], 0
    for f in files:
        block = f"\n### FILE: {f['path']}\n{read_file(root, f['path'])[:per_file]}\n"
        if used + len(block) > budget:
            break
        out.append(block)
        used += len(block)
    return "".join(out)


def tree_text(files: List[Dict]) -> str:
    return "\n".join(f["path"] for f in files)
