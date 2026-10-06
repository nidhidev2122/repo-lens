# RepoLens — Local GitHub Repository Code Explainer

RepoLens helps you understand a public GitHub repository without staring at a wall of code.
Paste a repository URL and the app:

1. clones and scans the repository locally,
2. sends the relevant code to a local Ollama model,
3. explains the project in beginner-friendly language,
4. shows the project tree,
5. builds a one-glance flowchart, and
6. turns the important points into a large summary table.

The UI is intentionally minimal: **Home → Explain Repository → Code Structure → Summary → Flowchart**.
The old File Viewer and separate AI Explanation pages have been removed so the product stays focused on understanding the project rather than browsing individual files.

## Stack

- **Frontend:** Streamlit
- **Backend:** FastAPI + GitPython
- **Local AI:** Ollama + Qwen (`qwen2.5:3b` by default)
- **Diagram:** Mermaid

## Project structure

```text
repolens/
├── .streamlit/
│   └── config.toml
├── backend/
│   ├── llm_service.py
│   ├── main.py
│   ├── repo_processor.py
│   ├── schemas.py
│   ├── test_llm.py
│   └── test_repo.py
├── frontend/
│   └── app.py
├── requirements.txt
└── README.md
```

## Run locally

### 1. Requirements

Install Python 3.10+, Git, and Ollama.

### 2. Create the environment

```bash
python -m venv venv
source venv/bin/activate
# Windows PowerShell:
# .\venv\Scripts\Activate.ps1

pip install -r requirements.txt
ollama pull qwen2.5:3b
```

### 3. Start the backend

From the project root:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 4. Start Streamlit

In a second terminal:

```bash
streamlit run frontend/app.py
```

Open `http://localhost:8501`.

If the backend is not on `localhost:8000`, set:

```bash
export REPOLENS_API="http://YOUR_BACKEND_HOST:8000"
```

On Windows PowerShell:

```powershell
$env:REPOLENS_API="http://YOUR_BACKEND_HOST:8000"
```

## Ollama settings

The backend reads these optional environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_MODEL` | `qwen2.5:3b` | Local model name |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `REPOLENS_API` | `http://localhost:8000` | Streamlit → FastAPI URL |

## Deploy

### Recommended: deploy the whole app on one Linux VPS

This is the cleanest production setup because Ollama needs to run somewhere reachable by the backend.

1. Create a Linux VPS with enough RAM for your chosen Ollama model. 8 GB RAM is a practical starting point for the 3B model.
2. Install Git, Python, Ollama, and the project dependencies.
3. Pull the model:

```bash
ollama pull qwen2.5:3b
```

4. Start FastAPI on an internal port:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

5. Start Streamlit:

```bash
streamlit run frontend/app.py --server.address 0.0.0.0 --server.port 8501
```

6. Put Nginx/Caddy in front of Streamlit and expose HTTPS. Keep Ollama and FastAPI private unless you specifically need them public.
7. Use a process manager such as `systemd` or `supervisord` so the backend, Ollama, and Streamlit restart automatically.

### Quick demo: Streamlit Cloud + your own backend

Streamlit Cloud cannot run Ollama itself. For a demo, keep Ollama + FastAPI on your machine/server and expose **only FastAPI** through a secure HTTPS tunnel or hosted service.

Then add this Streamlit secret:

```toml
REPOLENS_API = "https://your-backend.example.com"
```

Do not expose your Ollama port (`11434`) directly to the public internet.

## Notes

- Only public GitHub repositories are supported by the current URL parser.
- Repository files are cloned into `cloned_repos/` and should not be committed.
- The app intentionally analyzes relevant source/config files instead of presenting a full file browser.
- The model is local, so analysis quality and speed depend on the Ollama model and machine.
