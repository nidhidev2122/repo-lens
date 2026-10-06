"""RepoLens — a focused Streamlit UI for understanding public GitHub repositories."""

import html
import os
import re
from typing import Dict, List

import requests
import streamlit as st
import streamlit.components.v1 as components


def _api_url() -> str:
    try:
        return st.secrets["REPOLENS_API"]
    except Exception:
        return os.environ.get("REPOLENS_API", "http://localhost:8000")


API = _api_url().rstrip("/")
st.set_page_config(page_title="RepoLens — Code Explainer", page_icon="🔑", layout="wide")

# ---------------------------------------------------------------------------
# Visual system: near-black + burnt orange, with restrained motion.
CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
  --bg: #090706;
  --bg-2: #100b08;
  --panel: #15100d;
  --panel-2: #1b130f;
  --line: #34231b;
  --line-hot: #6b3520;
  --orange: #ff6a2a;
  --orange-2: #ff8a3d;
  --orange-soft: #ffb17c;
  --cream: #fff6ee;
  --muted: #b09a8c;
  --green: #5fd18a;
}

html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
.stApp {
  background:
    radial-gradient(circle at 80% 5%, rgba(255,106,42,.13), transparent 28%),
    radial-gradient(circle at 5% 85%, rgba(255,106,42,.07), transparent 25%),
    linear-gradient(145deg, var(--bg), #070505 65%);
  color: var(--cream);
}
.stApp::before {
  content: ""; position: fixed; inset: 0; pointer-events: none; opacity: .22;
  background-image: radial-gradient(rgba(255,255,255,.18) .7px, transparent .7px);
  background-size: 28px 28px; animation: drift 18s linear infinite;
}
@keyframes drift { from { transform: translate(0,0); } to { transform: translate(28px,28px); } }
@keyframes rise { from { opacity:0; transform:translateY(16px); } to { opacity:1; transform:translateY(0); } }
@keyframes glow { 0%,100% { box-shadow: 0 0 0 rgba(255,106,42,0); } 50% { box-shadow: 0 0 32px rgba(255,106,42,.16); } }
@keyframes pulse { 0%,100% { opacity:.55; transform:scale(.98); } 50% { opacity:1; transform:scale(1); } }

header[data-testid="stHeader"] { background: transparent; }
section[data-testid="stSidebar"] {
  background: rgba(9,7,6,.94); border-right: 1px solid var(--line);
}
section[data-testid="stSidebar"] > div { padding-top: 1.4rem; }

/* Sidebar */
.brand { display:flex; align-items:center; gap:.7rem; margin:.15rem 0 1.6rem; }
.brand-name { font-size:1.35rem; font-weight:700; letter-spacing:-.04em; }
.brand-name span { color:var(--orange); }
.cat-mark {
  width:42px; height:42px; border-radius:13px; position:relative; display:flex; align-items:center; justify-content:center;
  background:linear-gradient(145deg,#ff7b39,#c73f13); box-shadow:0 10px 28px rgba(255,106,42,.22);
  animation: glow 4s ease-in-out infinite;
}
.cat-mark::before { content:""; width:18px; height:15px; border-radius:48% 48% 45% 45%; background:#0d0907; position:absolute; bottom:9px; }
.cat-mark::after { content:"•  •"; position:absolute; color:#fff0e7; font-size:10px; letter-spacing:2px; bottom:12px; }
.cat-ear { position:absolute; width:9px; height:11px; background:#0d0907; top:9px; transform:rotate(26deg); clip-path:polygon(0 100%, 45% 0, 100% 100%); }
.cat-ear.left { left:10px; } .cat-ear.right { right:10px; transform:rotate(-26deg); }

.nav-caption { color:#705b4e; text-transform:uppercase; letter-spacing:.13em; font-size:.68rem; margin:1.3rem .2rem .5rem; }
.stButton > button {
  border-radius:13px; border:1px solid transparent; padding:.72rem .9rem; font-weight:600;
  transition: transform .2s ease, border-color .2s ease, background .2s ease, box-shadow .2s ease;
}
.stButton > button:hover { transform:translateY(-2px); }
.stButton > button[kind="secondary"] { background:transparent; color:#c7b5a9; border-color:transparent; }
.stButton > button[kind="secondary"]:hover { background:#17100d; border-color:var(--line); color:#fff; }
.stButton > button[kind="primary"] {
  background:linear-gradient(135deg,#ff7130,#e64c16); color:white; border-color:#ff8147;
  box-shadow:0 8px 28px rgba(255,106,42,.22);
}
.stButton > button[kind="primary"]:hover { box-shadow:0 12px 34px rgba(255,106,42,.35); filter:brightness(1.05); }
.main .stButton > button { width:auto; }

/* Home */
.home-shell { min-height:76vh; display:flex; align-items:center; padding:4rem 0 5rem; animation:rise .65s ease both; }
.home-copy { max-width:1050px; }
.home-kicker { color:var(--orange); font-family:'DM Mono',monospace; font-size:.82rem; letter-spacing:.18em; text-transform:uppercase; margin-bottom:1.3rem; }
.home-title { font-size:clamp(3.8rem, 7vw, 7.4rem); line-height:.9; letter-spacing:-.075em; font-weight:700; margin:0; }
.home-title .orange { color:var(--orange); }
.home-subtitle { max-width:920px; color:#d1beb1; font-size:clamp(1.05rem,1.6vw,1.35rem); line-height:1.65; margin:2rem 0 2.3rem; }
.home-button .stButton > button { font-size:1rem; padding:.95rem 1.5rem; border-radius:15px; }

/* Shared cards */
.page-enter { animation:rise .5s ease both; }
.section-title { font-size:3rem; letter-spacing:-.055em; margin:.2rem 0 .4rem; font-weight:700; }
.section-lede { color:var(--muted); font-size:1.02rem; margin-bottom:2rem; }
.eyebrow { color:var(--orange); font-family:'DM Mono',monospace; text-transform:uppercase; letter-spacing:.12em; font-size:.72rem; }
.glass {
  background:linear-gradient(145deg, rgba(27,19,15,.96), rgba(14,10,8,.96));
  border:1px solid var(--line); border-radius:22px; padding:1.5rem; animation:rise .55s ease both;
}
.glass:hover { border-color:var(--line-hot); box-shadow:0 18px 55px rgba(0,0,0,.25); }
.step-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:1rem; margin:1.7rem 0 2.2rem; }
.step-card { position:relative; min-height:190px; background:var(--panel); border:1px solid var(--line); border-radius:20px; padding:1.35rem; transition:.25s ease; overflow:hidden; }
.step-card::after { content:""; position:absolute; width:90px; height:90px; right:-35px; bottom:-40px; border-radius:50%; background:rgba(255,106,42,.13); filter:blur(4px); }
.step-card:hover { transform:translateY(-7px); border-color:#824125; box-shadow:0 18px 45px rgba(255,106,42,.08); }
.step-number { width:34px; height:34px; border-radius:10px; display:grid; place-items:center; background:#28150d; color:var(--orange); font-family:'DM Mono',monospace; border:1px solid #5a2a19; }
.step-card h3 { margin:.9rem 0 .45rem; font-size:1.05rem; }
.step-card p { color:#9e897c; line-height:1.55; margin:0; }

/* Input / repo page */
div[data-baseweb="input"] { background:#0d0907; border:1px solid #40291e; border-radius:15px; }
div[data-baseweb="input"]:focus-within { border-color:var(--orange); box-shadow:0 0 0 3px rgba(255,106,42,.1); }
input { color:#fff !important; }
.repo-box { padding:1.35rem; border-radius:22px; background:linear-gradient(145deg,#1b120e,#100b08); border:1px solid #4b2b1d; box-shadow:0 16px 50px rgba(0,0,0,.22); }
.analyze-row { margin-top:.6rem; }
.result-heading { margin-top:2.5rem; font-size:1.55rem; letter-spacing:-.03em; }
.explanation {
  white-space:pre-wrap; color:#d9c8bc; line-height:1.72; font-size:1rem; background:#0d0907;
  border:1px solid var(--line); border-left:3px solid var(--orange); border-radius:18px; padding:1.5rem 1.6rem;
}

/* Tree */
.tree { background:#0c0907; border:1px solid var(--line); border-radius:22px; padding:1.5rem 1.7rem; font-family:'DM Mono',monospace; overflow:auto; }
.tree-line { white-space:pre; line-height:1.95; color:#bda99d; transition:color .18s ease, transform .18s ease; }
.tree-line:hover { color:#fff2e8; transform:translateX(4px); }
.tree-folder { color:var(--orange); font-weight:500; }
.tree-file { color:#cdbcb1; }
.tree-root { color:#fff; font-weight:600; }

/* Summary */
.summary-table { width:100%; border-collapse:separate; border-spacing:0; overflow:hidden; border:1px solid var(--line); border-radius:22px; background:#0d0907; }
.summary-table td { padding:1.25rem 1.35rem; border-bottom:1px solid #241914; vertical-align:top; line-height:1.6; }
.summary-table tr:last-child td { border-bottom:0; }
.summary-table td:first-child { width:24%; color:var(--orange-soft); font-family:'DM Mono',monospace; font-size:.8rem; text-transform:uppercase; letter-spacing:.08em; background:#120c09; }
.summary-table td:last-child { color:#d9c8bc; font-size:1rem; }
.stats { display:grid; grid-template-columns:repeat(3,1fr); gap:1rem; margin:1.3rem 0 2rem; }
.stat { background:var(--panel); border:1px solid var(--line); border-radius:18px; padding:1.2rem 1.3rem; }
.stat b { display:block; font-size:2rem; color:#fff; letter-spacing:-.05em; }
.stat span { color:#8f786a; font-size:.78rem; text-transform:uppercase; letter-spacing:.08em; }

/* Flow */
.flow-shell { background:#0b0806; border:1px solid var(--line); border-radius:24px; padding:1rem; min-height:520px; box-shadow:inset 0 0 80px rgba(255,106,42,.035); }
.flow-note { color:#8e7669; font-size:.88rem; margin-top:.8rem; }

@media (max-width: 900px) {
  .step-grid, .stats { grid-template-columns:1fr; }
  .home-title { font-size:3.8rem; }
  .summary-table td { display:block; width:auto !important; }
  .summary-table td:first-child { border-bottom:0; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# State + API helpers
S = st.session_state
for key, default in {"page": "Home", "repo": None, "explanation": None, "mermaid": None}.items():
    S.setdefault(key, default)

PAGES = ["Home", "Explain Repository", "Code Structure", "Summary", "Flowchart"]


def call(method: str, path: str, **kwargs):
    try:
        response = requests.request(method, f"{API}{path}", timeout=700, **kwargs)
    except requests.ConnectionError as err:
        raise RuntimeError("Cannot reach the backend. Start it with: uvicorn backend.main:app --port 8000") from err
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(detail)
    return response.json()


def need_repo() -> bool:
    if not S.repo:
        st.info("Analyze a repository first from **Explain Repository**.")
        return True
    return False


def escape(value: str) -> str:
    return html.escape(str(value), quote=True)


def parse_explanation(text: str) -> Dict[str, str]:
    """Turn the model's stable headings into table rows without assuming prose."""
    sections: Dict[str, List[str]] = {}
    current = "Overview"
    sections[current] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        normalized = line.rstrip(":").lower()
        if normalized in {"project overview", "the application allows users to", "main technologies", "how it works"}:
            current = line.rstrip(":")
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(line)
    return {key: "<br>".join(escape(v) for v in values) for key, values in sections.items() if values}


def tree_lines(paths: List[str]) -> List[str]:
    """Build a readable git-style tree from repository paths."""
    root: dict = {}
    for path in sorted(paths):
        node = root
        for part in path.split("/"):
            node = node.setdefault(part, {})

    lines: List[str] = []

    def walk(node: dict, prefix: str = "", root_level: bool = False):
        items = list(node.items())
        for index, (name, children) in enumerate(items):
            last = index == len(items) - 1
            branch = "└── " if last else "├── "
            is_folder = bool(children)
            cls = "tree-folder" if is_folder else "tree-file"
            if root_level and index == 0:
                cls = "tree-root"
            visible = prefix + branch + name + ("/" if is_folder else "")
            lines.append(f'<div class="tree-line"><span class="{cls}">{escape(visible)}</span></div>')
            if is_folder:
                walk(children, prefix + ("    " if last else "│   "))

    walk(root, root_level=True)
    return lines


def render_mermaid(code: str, height: int = 620):
    safe_code = escape(code)
    html_block = f"""
    <div class=\"flow-shell\">
      <pre class=\"mermaid\" style=\"margin:0;\">{safe_code}</pre>
    </div>
    <script type=\"module\">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
      mermaid.initialize({{
        startOnLoad:true, securityLevel:'loose', theme:'base',
        flowchart:{{useMaxWidth:true, htmlLabels:true, curve:'basis'}},
        themeVariables:{{
          background:'#0b0806', primaryColor:'#24130b', primaryTextColor:'#fff2e8',
          primaryBorderColor:'#ff6a2a', lineColor:'#b9582b', secondaryColor:'#160e0a',
          tertiaryColor:'#120c09', fontFamily:'Space Grotesk, sans-serif'
        }}
      }});
    </script>"""
    components.html(html_block, height=height, scrolling=True)


# ---------------------------------------------------------------------------
# Sidebar
with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="cat-mark"><i class="cat-ear left"></i><i class="cat-ear right"></i></div>'
        '<div class="brand-name">Repo<span>Lens</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="nav-caption">Navigate</div>', unsafe_allow_html=True)
    for label in PAGES:
        if st.button(label, key=f"nav_{label}", type="primary" if S.page == label else "secondary", use_container_width=True):
            S.page = label
            st.rerun()

# ---------------------------------------------------------------------------
# Pages
if S.page == "Home":
    st.markdown(
        '<div class="home-shell page-enter"><div class="home-copy">'
        '<h1 class="home-title">Local GitHub Repository<br><span class="orange">Code Explainer</span></h1>'
        '<p class="home-subtitle">Don’t Understand the Code? Let AI Explain It.<br>'
        'Drop in any public GitHub repository and get a simple, easy-to-understand breakdown of what the project does and how the code works!</p>'
        '<div class="home-button">', unsafe_allow_html=True
    )
    if st.button("Get started  →", type="primary"):
        S.page = "Explain Repository"
        st.rerun()
    st.markdown('</div></div></div>', unsafe_allow_html=True)

elif S.page == "Explain Repository":
    st.markdown('<div class="page-enter">', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">01 / Understand the repo</div><h1 class="section-title">Explain Repository</h1>'
                '<p class="section-lede">Paste a public GitHub link. We scan the project, read the important files, and explain the whole thing in plain English.</p>', unsafe_allow_html=True)
    st.markdown('<div class="repo-box">', unsafe_allow_html=True)
    url = st.text_input("GitHub repository URL", placeholder="https://github.com/username/repository", label_visibility="collapsed")
    st.markdown('<div class="analyze-row">', unsafe_allow_html=True)
    if st.button("Analyze repository  →", type="primary"):
        if not url.strip():
            st.error("Paste a public GitHub repository URL first.")
        else:
            try:
                with st.spinner("Cloning and scanning the repository…"):
                    S.repo = call("POST", "/analyze", json={"repo_url": url.strip()})
                S.explanation = S.mermaid = None
                with st.spinner("Reading the code with your local AI…"):
                    S.explanation = call("POST", "/explain", json={"repo_id": S.repo["repo_id"]})["explanation"]
                st.rerun()
            except Exception as err:
                st.error(str(err))
    st.markdown('</div></div>', unsafe_allow_html=True)

    st.markdown('<h2 class="result-heading">How it works</h2>', unsafe_allow_html=True)
    st.markdown(
        '<div class="step-grid">'
        '<div class="step-card"><div class="step-number">01</div><h3>Drop the link</h3><p>Give RepoLens any public GitHub repository URL.</p></div>'
        '<div class="step-card"><div class="step-number">02</div><h3>Scan the project</h3><p>The app clones it locally and picks the files that matter most.</p></div>'
        '<div class="step-card"><div class="step-number">03</div><h3>Get the big picture</h3><p>A local AI explains the code, structure, key points, and flow.</p></div>'
        '</div>', unsafe_allow_html=True
    )

    if S.explanation:
        repo_name = escape(S.repo["repo_name"])
        st.markdown(f'<h2 class="result-heading">AI explanation <span style="color:#80685a;font-size:.8em">· {repo_name}</span></h2>', unsafe_allow_html=True)
        st.markdown(f'<div class="explanation">{escape(S.explanation)}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif S.page == "Code Structure":
    if not need_repo():
        st.markdown('<div class="page-enter">', unsafe_allow_html=True)
        st.markdown('<div class="eyebrow">02 / See the shape</div><h1 class="section-title">Code Structure</h1>'
                    '<p class="section-lede">No wall of code. Just the project tree, cleaned up so you can understand what lives where.</p>', unsafe_allow_html=True)
        paths = [f["path"] for f in S.repo["files"]]
        st.markdown('<div class="tree">' + ''.join(tree_lines(paths)) + '</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

elif S.page == "Summary":
    if not need_repo():
        st.markdown('<div class="page-enter">', unsafe_allow_html=True)
        st.markdown('<div class="eyebrow">03 / The cheat sheet</div><h1 class="section-title">Project Summary</h1>'
                    '<p class="section-lede">The important stuff, pulled into one big table so you can understand the repository at a glance.</p>', unsafe_allow_html=True)
        repo = S.repo
        st.markdown(
            f'<div class="stats">'
            f'<div class="stat"><b>{escape(repo["files_found"])}</b><span>Relevant files</span></div>'
            f'<div class="stat"><b>{escape(len(repo["languages"]))}</b><span>File types</span></div>'
            f'<div class="stat"><b>{escape(repo["repo_name"])}</b><span>Repository</span></div>'
            f'</div>', unsafe_allow_html=True)
        if not S.explanation:
            st.info("Run the analysis from **Explain Repository** first.")
        else:
            rows = parse_explanation(S.explanation)
            labels = {
                "Project Overview": "What is this?",
                "The application allows users to": "What can it do?",
                "Main Technologies": "Tech stack",
                "How it works": "How does it work?",
                "Overview": "Key points",
            }
            html_rows = []
            for key, value in rows.items():
                html_rows.append(f'<tr><td>{escape(labels.get(key, key))}</td><td>{value}</td></tr>')
            st.markdown('<table class="summary-table">' + ''.join(html_rows) + '</table>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

elif S.page == "Flowchart":
    if not need_repo():
        st.markdown('<div class="page-enter">', unsafe_allow_html=True)
        st.markdown('<div class="eyebrow">04 / Follow the flow</div><h1 class="section-title">Project Flowchart</h1>'
                    '<p class="section-lede">One diagram. One glance. See how the repository moves from input to output.</p>', unsafe_allow_html=True)
        if not S.mermaid and st.button("Generate flowchart  →", type="primary"):
            try:
                with st.spinner("Mapping the project…"):
                    result = call("POST", "/flowchart", json={"repo_id": S.repo["repo_id"]})
                S.mermaid = result["mermaid"]
                if result["source"] == "fallback":
                    st.warning("The AI diagram could not be validated, so a clean structural overview was generated instead.")
                st.rerun()
            except Exception as err:
                st.error(str(err))
        if S.mermaid:
            render_mermaid(S.mermaid)
            st.markdown('<div class="flow-note">Tip: read left-to-right from the user input to the final output. The orange nodes are the main moving parts.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
