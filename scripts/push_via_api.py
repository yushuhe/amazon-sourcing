"""Push current git tree to GitHub via REST API (when git push is blocked)."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

OWNER = "yushuhe"
REPO = "amazon-sourcing"
BRANCH = "main"
MESSAGE = "Fix Vercel: use api/index.py entrypoint and EdgeOne same-origin API"


def api(method: str, path: str, body: dict | None = None) -> dict:
    token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN") or os.environ.get(
        "GITHUB_TOKEN"
    )
    if not token:
        raise SystemExit("GITHUB_PERSONAL_ACCESS_TOKEN not set")

    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normalize_path(raw: str) -> str | None:
    path = raw.strip().strip('"')
    if not path or path in {"\r", "\n", "\r\n"}:
        return None
    if "\\344\\275\\277" in path:
        return "使用说明.md"
    return path


def list_index_blobs() -> list[tuple[str, str]]:
    out = subprocess.check_output(["git", "ls-files", "--stage"], text=True)
    items: list[tuple[str, str]] = []
    for line in out.splitlines():
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        blob_sha = parts[0].split()[1]
        path = normalize_path(parts[1])
        if path:
            items.append((path, blob_sha))
    return items


def git_blob_bytes(blob_sha: str) -> bytes:
    return subprocess.check_output(["git", "cat-file", "-p", blob_sha])


def main() -> None:
    ref = api("GET", f"/repos/{OWNER}/{REPO}/git/ref/heads/{BRANCH}")
    parent_sha = ref["object"]["sha"]

    tree_items = []
    for rel, blob_sha in list_index_blobs():
        if not rel.strip():
            continue
        content = git_blob_bytes(blob_sha)
        blob = api(
            "POST",
            f"/repos/{OWNER}/{REPO}/git/blobs",
            {"content": base64.b64encode(content).decode("ascii"), "encoding": "base64"},
        )
        tree_items.append(
            {"path": rel.replace("\\", "/"), "mode": "100644", "type": "blob", "sha": blob["sha"]}
        )
        print(f"  blob: {rel}")

    tree = api("POST", f"/repos/{OWNER}/{REPO}/git/trees", {"tree": tree_items})
    commit = api(
        "POST",
        f"/repos/{OWNER}/{REPO}/git/commits",
        {"message": MESSAGE, "tree": tree["sha"], "parents": [parent_sha]},
    )
    api(
        "PATCH",
        f"/repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}",
        {"sha": commit["sha"]},
    )
    print(f"\nDone: https://github.com/{OWNER}/{REPO}/commit/{commit['sha']}")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        print(exc.read().decode("utf-8", errors="replace"), file=sys.stderr)
        raise SystemExit(1) from exc
