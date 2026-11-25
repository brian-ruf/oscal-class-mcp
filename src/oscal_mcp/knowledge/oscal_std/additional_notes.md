<!-- notes-version: 1.0.0 | updated: 2026-11-24 -->
# Additional Notes — Expert Enhancements to the OSCAL Standard

**Notes version:** 1.0.0 · **Updated:** 2026-11-24

These notes are **authored expert commentary**, not NIST-published content. They capture
caveats, known gaps, draft-status warnings, and practical guidance that the official
OSCAL documentation (bundled under `oscal-std://concepts`) does not state explicitly or
states only implicitly. Read them alongside the NIST pages, not instead of them.

> **Maintenance policy.** This file is hand-curated and is **never overwritten** by
> `scripts/sync_knowledge.py`. Every substantive change here is a release-worthy event:
> add/update a note, bump `notes-version` (semver) in the top comment and the heading,
> add a changelog row, and **bump the oscal-mcp package version** in `pyproject.toml`.
> See `docs/MAINTAINING_KNOWLEDGE.md`.

## Changelog

| notes-version | oscal-mcp version | date       | change |
|---------------|-------------------|------------|--------|
| 1.0.0         | 1.1.0             | 2026-11-24 | Initial notes: profile spec draft status & child-group directive gap. |

---

## Notes

### N-001 — The profile model specification is still effectively draft, with known gaps
- **Applies to:** profile (control layer); OSCAL 1.x.
- **Status:** NIST documentation presents profile resolution as settled, but the
  profile *resolution specification* has long-standing open issues and should be treated
  as **not fully finalized**. Tool behavior varies where the spec is silent.
- **Detail — child groups under directives.** The specification does not fully define how
  **child groups** are handled under certain profile directives (e.g. `include-all`,
  `insert-controls`/`as-is` structuring, and `alter` targeting). In particular, whether a
  nested group is preserved, flattened, or reparented when only some of its descendant
  controls are selected is under-specified, and resolvers differ. The `oscal` library
  makes this explicit through its merge strategy (`REFERENTIAL` vs `POSITIONAL`; see
  `oscal-lib://concepts/profile-processing`) — a point the NIST pages do not surface.
- **Guidance for agents:** when generating or resolving profiles, do not assume a single
  canonical child-group outcome. State the assumed merge strategy, prefer explicit
  `insert-controls`/structuring directives over relying on implicit hierarchy, and
  validate the resolved catalog rather than trusting the directive semantics alone.

<!-- Template for new notes — copy below, assign the next N-### id:

### N-### — <concise title>
- **Applies to:** <model(s) / layer / OSCAL version(s)>
- **Status:** <draft / gap / ambiguity / common-misuse / tooling-divergence>
- **Detail:** <what the NIST docs omit or get wrong, specifically>
- **Guidance for agents:** <what to do in practice>

-->
