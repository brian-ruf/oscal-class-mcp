#!/usr/bin/env python3
"""Dev/release-time tool to bundle offline documentation into ``oscal_mcp/knowledge/``.

This script is **not** imported at runtime. The MCP server serves the bundled snapshot
offline; this is how a maintainer refreshes that snapshot.

Collections:
* ``oscal-lib`` — the ``oscal`` library's operating-concept guides (from ``oscal-class/docs``),
  kept in parity with the library release the server wraps.
* ``oscal-std`` — a curated snapshot of the NIST OSCAL standard "Learn" pages (from
  ``usnistgov/OSCAL-Pages``). Hugo front-matter and USWDS shortcodes are stripped. The
  authored ``additional_notes.md`` and ``NIST-ATTRIBUTION.md`` in that directory are
  **never** overwritten.

Sources:
* ``--from-local <checkout>`` — copy from a local ``oscal-class`` checkout (oscal-lib only).
* ``--from-release <ref>`` — download from ``raw.githubusercontent.com/<repo>/<ref>/...``
  (public repo; dev-time network only).

For ``oscal-std``, a plain sync resolves the tracked branch's latest commit that touches the
content path and pins that exact SHA in the manifest — so new builds pick up the latest NIST
content by default, while remaining reproducible. The manifest is the repo's **memory** of
what was bundled; ``--check`` compares it against upstream without writing anything (use it
as a build-time gate).

Examples::

    python scripts/sync_knowledge.py oscal-lib --from-local /work/rr/class --release v4.3.0
    python scripts/sync_knowledge.py oscal-std --check     # is newer NIST content available?
    python scripts/sync_knowledge.py oscal-std             # incorporate the latest (pins the SHA)
    python scripts/sync_knowledge.py oscal-std --from-release <sha-or-tag>   # pin a specific ref
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = REPO_ROOT / "src" / "oscal_mcp" / "knowledge"

# Allow-list of library operating-concept guides (order = reading order in the index).
OSCAL_LIB = {
    "kind": "lib",
    "collection": "oscal_lib",
    "repo": "brian-ruf/oscal-class",
    "src_subdir": "docs",
    "uri_prefix": "oscal-lib://concepts",
    "files": [
        "OVERVIEW.md",
        "CONOPS.md",
        "GETTING_STARTED.md",
        "CONTENT.md",
        "VALIDATION.md",
        "IMPORTS.md",
        "IMPORT_SELECTION_API.md",
        "IMPORTING_CONTROLS.md",
        "PROFILE_PROCESSING.md",
        "QUERY_CONTENT.md",
        "CONVERTERS.md",
        "SUPPORT_MODULE.md",
        "SHARED_MODE.md",
        "METHOD_PATTERNS.md",
        "LOGGING.md",
    ],
}

# Curated NIST OSCAL "Learn" pages: (source path under src_subdir, bundled slug).
# Titles come from each page's front-matter.
OSCAL_STD = {
    "kind": "std",
    "collection": "oscal_std",
    "repo": "usnistgov/OSCAL-Pages",
    "src_subdir": "src/content/learn",
    "uri_prefix": "oscal-std://concepts",
    # Upstream branch to track. A plain `sync oscal-std` resolves this branch's latest
    # commit that touches the content path and pins that exact SHA in the manifest (so the
    # snapshot is reproducible); `--from-release <ref>` overrides with a specific ref.
    "branch": "main",
    "license": "Public Domain (US Gov, 17 USC 105) / CC0 1.0",
    "attribution_file": "NIST-ATTRIBUTION.md",
    "notes_file": "additional_notes.md",
    "pages": [
        ("concepts/_index.md", "concepts-overview"),
        ("concepts/layer/overview.md", "layers-and-models"),
        ("concepts/layer/control/_index.md", "control-layer"),
        ("concepts/layer/control/catalog/_index.md", "catalog"),
        ("concepts/layer/control/profile/_index.md", "profile"),
        ("concepts/layer/control/mapping/_index.md", "mapping"),
        ("concepts/layer/implementation/_index.md", "implementation-layer"),
        ("concepts/layer/implementation/component-definition/_index.md", "component-definition"),
        ("concepts/layer/implementation/ssp/_index.md", "ssp"),
        ("concepts/layer/assessment/_index.md", "assessment-layer"),
        ("concepts/layer/assessment/assessment-plan/_index.md", "assessment-plan"),
        ("concepts/layer/assessment/assessment-results/_index.md", "assessment-results"),
        ("concepts/layer/assessment/poam/_index.md", "poam"),
        ("concepts/terminology/_index.md", "terminology"),
        ("concepts/identifier-use/_index.md", "identifier-use"),
        ("concepts/uri-use.md", "uri-use"),
        ("concepts/processing/_index.md", "processing"),
        ("concepts/validation/_index.md", "validation"),
        ("concepts/relations-to-other.md", "relations-to-other-standards"),
        ("tutorials/control/basic-catalog.md", "tutorial-catalog"),
        ("tutorials/control/basic-profile.md", "tutorial-profile"),
        ("tutorials/general/metadata.md", "tutorial-metadata"),
        ("tutorials/general/extension.md", "tutorial-extension"),
        ("tutorials/implementation/simple-component-definition.md", "tutorial-component-definition"),
        ("tutorials/implementation/validation-modeling.md", "tutorial-validation-modeling"),
    ],
}

COLLECTIONS = {"oscal-lib": OSCAL_LIB, "oscal-std": OSCAL_STD}


# -----------------------------------------------------------------------------
# Text helpers
# -----------------------------------------------------------------------------
def strip_front_matter(text: str) -> Tuple[str, Optional[str]]:
    """Remove a leading ``---`` (YAML) or ``+++`` (TOML) front-matter block.

    Returns ``(body, title-or-None)`` using the first top-level ``title`` key found.
    """
    title: Optional[str] = None
    lines = text.splitlines()
    delim = lines[0].strip() if lines else ""
    if delim in ("---", "+++"):
        end = None
        for i in range(1, len(lines)):
            if lines[i].strip() == delim:
                end = i
                break
        if end is not None:
            for fm in lines[1:end]:
                stripped = fm.strip()
                if stripped.startswith("#"):  # YAML comment
                    continue
                low = stripped.lower()
                if title is None and low.startswith("title:"):
                    title = stripped.split(":", 1)[1].strip().strip("\"'")
                elif title is None and (low.startswith("title=") or low.startswith("title ")):
                    if "=" in stripped:
                        title = stripped.split("=", 1)[1].strip().strip("\"'")
            lines = lines[end + 1 :]
    body = "\n".join(lines).lstrip("\n")
    if title is None:
        for ln in body.splitlines():
            if ln.startswith("# "):
                title = ln[2:].strip()
                break
    return body, title


def clean_hugo(text: str) -> Tuple[str, Optional[str]]:
    """Convert a Hugo page to plain markdown: strip front-matter, shortcodes, comments."""
    body, title = strip_front_matter(text)
    body = re.sub(r"{{%[^}]*?%}}", "", body)  # {{% usa-grid-row %}} etc.
    body = re.sub(r"{{<[^}]*?>}}", "", body)  # {{< figure ... >}} etc.
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    body = re.sub(r"[ \t]+\n", "\n", body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"
    return body, title


def slugify(filename: str) -> str:
    """``IMPORT_SELECTION_API.md`` -> ``import-selection-api``."""
    return Path(filename).stem.lower().replace("_", "-")


def rewrite_internal_links(body: str, uri_prefix: str, html_to_slug: Dict[str, str]) -> str:
    """Rewrite Jekyll cross-links (``FILE.html``) to bundled docs into resource URIs.

    Only links whose target is a bundled doc are rewritten (anchors dropped, since the
    resource returns the whole guide); all other links are left untouched.
    """

    def repl(m: re.Match) -> str:
        stem = m.group("stem")
        slug = html_to_slug.get(stem.lower())
        if slug is None:
            return m.group(0)
        return f"]({uri_prefix}/{slug})"

    return re.sub(r"\]\((?P<stem>[A-Za-z0-9_\-]+)\.html(?:#[^)]*)?\)", repl, body)


def parse_notes_version(text: str) -> Optional[str]:
    """Extract ``notes-version`` from the authored notes file's top HTML comment."""
    m = re.search(r"notes-version:\s*([0-9]+(?:\.[0-9]+)*)", text)
    return m.group(1) if m else None


# -----------------------------------------------------------------------------
# Fetchers
# -----------------------------------------------------------------------------
def fetch_local(checkout: Path, subdir: str, relpath: str) -> str:
    return (checkout / subdir / relpath).read_text(encoding="utf-8")


def fetch_release(repo: str, ref: str, subdir: str, relpath: str) -> str:
    url = f"https://raw.githubusercontent.com/{repo}/{ref}/{subdir}/{relpath}"
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310 - fixed https host
        return resp.read().decode("utf-8")


def _gh_api(url: str):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "oscal-mcp-sync"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - fixed https host
        return json.loads(resp.read().decode("utf-8"))


def latest_commit(repo: str, branch: str, path: str) -> Tuple[str, Optional[str]]:
    """Return ``(sha, iso-date)`` of the newest commit on ``branch`` touching ``path``."""
    url = f"https://api.github.com/repos/{repo}/commits?sha={branch}&path={path}&per_page=1"
    data = _gh_api(url)
    if not data:
        raise RuntimeError(f"No commits found for {repo}@{branch} touching {path}.")
    commit = data[0]
    return commit["sha"], commit.get("commit", {}).get("committer", {}).get("date")


def _read_manifest(out_dir: Path) -> dict:
    path = out_dir / "_manifest.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_manifest(out_dir: Path, manifest: dict) -> None:
    (out_dir / "_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


# -----------------------------------------------------------------------------
# Collection syncers
# -----------------------------------------------------------------------------
def sync_lib(cfg: dict, args: argparse.Namespace) -> int:
    out_dir = KNOWLEDGE_DIR / cfg["collection"]
    out_dir.mkdir(parents=True, exist_ok=True)
    html_to_slug = {Path(f).stem.lower(): slugify(f) for f in cfg["files"]}

    documents: List[dict] = []
    for filename in cfg["files"]:
        if args.from_local:
            raw = fetch_local(Path(args.from_local), cfg["src_subdir"], filename)
            source_ref = f"local:{args.from_local}"
        else:
            raw = fetch_release(cfg["repo"], args.from_release, cfg["src_subdir"], filename)
            source_ref = f"{cfg['repo']}@{args.from_release}:{cfg['src_subdir']}/{filename}"
        body, title = strip_front_matter(raw)
        body = rewrite_internal_links(body, cfg["uri_prefix"], html_to_slug)
        name = slugify(filename)
        (out_dir / f"{name}.md").write_text(body, encoding="utf-8")
        documents.append(
            {
                "name": name,
                "title": title or name.replace("-", " ").title(),
                "file": f"{name}.md",
                "source": f"{cfg['src_subdir']}/{filename}",
                "source_ref": source_ref,
                "words": len(body.split()),
            }
        )
        print(f"  + {name}.md  ({documents[-1]['words']} words)")

    release = args.release or args.from_release or "unknown"
    _write_manifest(
        out_dir,
        {
            "collection": cfg["collection"],
            "source_repo": cfg["repo"],
            "source_release": release,
            "synced": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generator": "scripts/sync_knowledge.py",
            "documents": documents,
        },
    )
    print(f"Wrote {len(documents)} docs + manifest to {out_dir} (release {release}).")
    return 0


def check_std(cfg: dict, args: argparse.Namespace) -> int:
    """Report whether upstream NIST content is newer than what the repo has bundled.

    Exit codes: ``0`` up-to-date, ``1`` update available, ``2`` check failed (e.g. network).
    """
    out_dir = KNOWLEDGE_DIR / cfg["collection"]
    man = _read_manifest(out_dir)
    bundled_ref = man.get("source_ref")
    branch = args.branch or cfg["branch"]
    try:
        sha, date = latest_commit(cfg["repo"], branch, cfg["src_subdir"])
    except Exception as exc:  # noqa: BLE001 - surface any network/API failure as code 2
        print(f"CHECK FAILED: could not query {cfg['repo']}@{branch}: {exc}")
        return 2

    print(f"bundled:  {bundled_ref or '(none)'}  (synced {man.get('synced', '?')})")
    print(f"upstream: {sha}  ({date}) on {cfg['repo']}@{branch}:{cfg['src_subdir']}")
    if bundled_ref == sha:
        print("UP-TO-DATE: bundled NIST content matches the latest upstream commit.")
        return 0
    print("UPDATE AVAILABLE: run `python scripts/sync_knowledge.py oscal-std` to incorporate it.")
    return 1


def sync_std(cfg: dict, args: argparse.Namespace) -> int:
    out_dir = KNOWLEDGE_DIR / cfg["collection"]
    out_dir.mkdir(parents=True, exist_ok=True)
    branch = args.branch or cfg["branch"]
    # Default to the latest commit on the tracked branch (so new builds pick up the latest);
    # --from-release pins an explicit ref instead.
    if args.from_release:
        ref, commit_date = args.from_release, None
    else:
        ref, commit_date = latest_commit(cfg["repo"], branch, cfg["src_subdir"])
        print(f"Resolved {cfg['repo']}@{branch} -> {ref} ({commit_date})")

    documents: List[dict] = []
    for relpath, slug in cfg["pages"]:
        raw = fetch_release(cfg["repo"], ref, cfg["src_subdir"], relpath)
        body, title = clean_hugo(raw)
        (out_dir / f"{slug}.md").write_text(body, encoding="utf-8")
        documents.append(
            {
                "name": slug,
                "title": title or slug.replace("-", " ").title(),
                "file": f"{slug}.md",
                "source": f"{cfg['src_subdir']}/{relpath}",
                "words": len(body.split()),
            }
        )
        print(f"  + {slug}.md  ({documents[-1]['words']} words)")

    # Register the authored expert notes (never fetched/overwritten here).
    notes_path = out_dir / cfg["notes_file"]
    notes_block = None
    if notes_path.is_file():
        notes_text = notes_path.read_text(encoding="utf-8")
        notes_version = parse_notes_version(notes_text)
        notes_block = {"file": cfg["notes_file"], "notes_version": notes_version, "authored": True}
        documents.append(
            {
                "name": "additional-notes",
                "title": "Additional Notes — Expert Enhancements (authored, not NIST)",
                "file": cfg["notes_file"],
                "authored": True,
                "notes_version": notes_version,
                "words": len(notes_text.split()),
            }
        )
        print(f"  = {cfg['notes_file']}  (authored, notes-version {notes_version})")
    else:
        print(f"  ! WARNING: authored {cfg['notes_file']} not found — expert notes will be absent.")

    _write_manifest(
        out_dir,
        {
            "collection": cfg["collection"],
            "source_repo": cfg["repo"],
            "source_branch": None if args.from_release else branch,
            "source_release": f"OSCAL-Pages@{ref[:12]}",
            "source_ref": ref,
            "source_commit_date": commit_date,
            "license": cfg["license"],
            "attribution_file": cfg["attribution_file"],
            "notes": notes_block,
            "synced": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generator": "scripts/sync_knowledge.py",
            "documents": documents,
        },
    )
    print(f"Wrote {len(documents)} docs + manifest to {out_dir} (OSCAL-Pages @ {ref[:12]}).")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Bundle offline docs into oscal_mcp/knowledge/.")
    parser.add_argument("collection", choices=sorted(COLLECTIONS), help="Which collection to sync.")
    parser.add_argument("--from-local", metavar="CHECKOUT", help="Path to a local oscal-class checkout (oscal-lib).")
    parser.add_argument("--from-release", metavar="REF", help="Git ref/tag to download from GitHub raw.")
    parser.add_argument(
        "--release",
        metavar="TAG",
        help="Release tag to stamp in the manifest (oscal-lib; defaults to --from-release).",
    )
    parser.add_argument("--branch", metavar="BRANCH", help="Upstream branch to track/check (oscal-std).")
    parser.add_argument(
        "--check",
        action="store_true",
        help="oscal-std: report whether upstream NIST content is newer than what is bundled "
        "(no writes). Exit 0=up-to-date, 1=update available, 2=check failed.",
    )
    args = parser.parse_args(argv)
    cfg = COLLECTIONS[args.collection]

    if cfg["kind"] == "lib":
        if args.check:
            parser.error("--check is only supported for oscal-std; oscal-lib parity is shown by oscal-lib://about.")
        if not (args.from_local or args.from_release):
            parser.error("oscal-lib requires --from-local or --from-release.")
        return sync_lib(cfg, args)

    if args.check:
        return check_std(cfg, args)
    return sync_std(cfg, args)


if __name__ == "__main__":
    sys.exit(main())
