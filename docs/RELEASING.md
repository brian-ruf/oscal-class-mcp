# Releasing `oscal-mcp`

Publishing mirrors the `oscal-class` two-workflow pattern:

- **`.github/workflows/publish.yml`** ("Release") — triggered by pushing a `vX.Y.Z` tag.
  Builds the sdist + wheel, verifies the tag matches `pyproject.toml [project].version`,
  runs a non-blocking NIST-content freshness check, and creates the **immutable GitHub
  Release** with the artifacts attached.
- **`.github/workflows/pypi.yml`** ("Publish to PyPI") — manually dispatched with the tag.
  Downloads the Release's `*.whl` / `*.tar.gz` and uploads them to PyPI (project
  `oscal-mcp`) via **Trusted Publishing (OIDC)** — no API token. Re-runnable
  (`skip-existing: true`).

## Maintainer flow

1. Bump `[project].version` in `pyproject.toml`. If the expert notes changed, also bump
   `notes-version` (see `docs/MAINTAINING_KNOWLEDGE.md`).
2. Refresh bundled knowledge if due: `python scripts/sync_knowledge.py oscal-std --check`
   (and `oscal-lib` parity via `oscal-lib://about`); re-sync if an update is available.
3. Merge to `main`, then tag and push:
   ```bash
   git tag vX.Y.Z && git push origin vX.Y.Z
   ```
   `publish.yml` builds and seals the GitHub Release.
4. From the Actions tab, run **Publish to PyPI** with `tag = vX.Y.Z` (or
   `gh workflow run pypi.yml -f tag=vX.Y.Z`).

## One-time setup (required before the first publish)

- **PyPI Trusted Publisher** for project `oscal-mcp`: owner/repo
  `brian-ruf/oscal-class-mcp`, workflow `pypi.yml`, environment `pypi`.
- A GitHub **`pypi` environment** on the repo (optionally with required reviewers for a
  manual approval gate).
- Ensure all runtime dependencies in `pyproject.toml` (notably `oscal`) are installable
  from PyPI, so `pip install oscal-mcp` resolves for end users. Building and publishing the
  artifact does not require this, but installing it does.

> Note: unlike `oscal-class`, this repo's Release workflow does not attach an SBOM
> (no `scripts/generate_sbom.sh`). Add an SBOM job mirroring oscal-class if/when desired.
