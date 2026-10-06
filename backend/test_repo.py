"""Quick check: clone a small repo and list the relevant files."""
from repo_processor import clone_repo, scan_files

repo_id, name, path = clone_repo("https://github.com/octocat/Hello-World")
files = scan_files(path)
print(f"Cloned {name}: {len(files)} relevant files")
for f in files:
    print(" -", f["path"])
