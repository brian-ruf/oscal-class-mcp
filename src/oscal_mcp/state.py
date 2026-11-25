"""Server state: OSCAL support-database configuration and the document cache.

Two responsibilities, both centralized here so the rest of the server never has to
think about them:

* **Support database.** The ``oscal`` library keeps a SQLite support database of the
  NIST metaschemas for every published OSCAL version/model. By default it lives at
  ``./support/oscal_support.db`` *relative to the current working directory* — but an
  MCP client may launch this server from an arbitrary CWD, so we pin the location to a
  stable per-user path and configure it **once, before any OSCAL object is created**
  (``configure_support_db``). ``db_init_mode="auto"`` lets the library auto-extract its
  bundled database on first run, so the server works offline out of the box.

* **Document cache.** ``DocumentStore`` wraps ``oscal.Workspace`` (the library's own
  stateful registry) and assigns every open document a stable string *handle* that MCP
  tools pass around. Re-opening the same source returns the same handle, mirroring the
  workspace's own de-duplication.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Optional

from platformdirs import user_data_dir

logger = logging.getLogger("oscal_mcp")

_ENV_SUPPORT_DB = "OSCAL_MCP_SUPPORT_DB"
_APP_NAME = "oscal-mcp"

# Guards so support configuration happens exactly once per process.
_support_lock = threading.Lock()
_support_configured = False
_support_db_path: Optional[str] = None


# -----------------------------------------------------------------------------
# Support database
# -----------------------------------------------------------------------------
def resolve_support_db_path(explicit: Optional[str] = None) -> str:
    """Resolve the support-database path.

    Precedence: ``explicit`` argument → ``OSCAL_MCP_SUPPORT_DB`` env var → a stable
    per-user default under the platform data directory (never the CWD).
    """
    candidate = explicit or os.environ.get(_ENV_SUPPORT_DB)
    if candidate:
        return os.path.abspath(os.path.expanduser(candidate))
    return os.path.join(user_data_dir(_APP_NAME), "support", "oscal_support.db")


def configure_support_db(path: Optional[str] = None, *, force: bool = False) -> str:
    """Configure the ``oscal`` library's support database. Idempotent.

    Must run before the first OSCAL object is created. Resolves the path (see
    :func:`resolve_support_db_path`), ensures the parent directory exists, and calls
    ``oscal.oscal_support.configure_support`` with ``db_init_mode="auto"`` so the
    bundled database is auto-extracted/built when absent.

    Returns the resolved path. Safe to call repeatedly; subsequent calls are no-ops
    unless ``force`` is set.
    """
    global _support_configured, _support_db_path
    with _support_lock:
        if _support_configured and not force:
            return _support_db_path  # type: ignore[return-value]

        db_path = resolve_support_db_path(path)
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Imported lazily so that merely importing this module does not pull in the
        # whole oscal package before the path is pinned.
        from oscal import oscal_support

        support = oscal_support.configure_support(support_file=db_path, db_init_mode="auto")
        state = getattr(support, "db_state", "unknown")
        logger.info("OSCAL support database configured at %s (state=%s)", db_path, state)

        _support_configured = True
        _support_db_path = db_path
        return db_path


def support_db_path() -> Optional[str]:
    """Return the configured support-database path, or ``None`` if not yet configured."""
    return _support_db_path


# -----------------------------------------------------------------------------
# Document cache
# -----------------------------------------------------------------------------
# Map of OSCAL model name -> the library class that loads/creates it. Used by
# ``new_document`` (creation needs a concrete subclass; loading can use the generic
# ``OSCAL`` base, which auto-detects the model).
def _model_class_map() -> dict:
    from oscal import (
        Catalog,
        Profile,
        Mapping,
        ComponentDefinition,
        SSP,
        AssessmentPlan,
        AssessmentResults,
        POAM,
    )

    return {
        "catalog": Catalog,
        "profile": Profile,
        "mapping-collection": Mapping,
        "component-definition": ComponentDefinition,
        "system-security-plan": SSP,
        "assessment-plan": AssessmentPlan,
        "assessment-results": AssessmentResults,
        "plan-of-action-and-milestones": POAM,
    }


class UnknownHandleError(KeyError):
    """Raised when a tool references a document handle that is not open."""


class DocumentStore:
    """Handle-addressed cache over an ``oscal.Workspace``.

    Handles are short, stable strings (``doc-1``, ``doc-2`` …). The same underlying
    OSCAL object always maps to the same handle, so re-opening a source that the
    workspace already has open returns the original handle rather than a duplicate.
    """

    def __init__(self) -> None:
        from oscal.oscal_workspace import Workspace

        self._ws = Workspace()
        self._by_handle: dict = {}  # handle -> OSCAL
        self._handle_by_id: dict = {}  # id(doc) -> handle
        self._counter = 0
        self._lock = threading.Lock()

    # -- registration ---------------------------------------------------------
    def _register(self, doc) -> str:
        """Return the handle for ``doc``, assigning a new one if first-seen."""
        with self._lock:
            existing = self._handle_by_id.get(id(doc))
            if existing is not None:
                return existing
            self._counter += 1
            handle = f"doc-{self._counter}"
            self._by_handle[handle] = doc
            self._handle_by_id[id(doc)] = handle
            return handle

    # -- opening / creating ---------------------------------------------------
    def open_path(self, source: str):
        """Open a local path or URI into the workspace. Returns ``(handle, doc)``."""
        doc = self._ws.open(source)
        return self._register(doc), doc

    def load_content(self, content, *, href: Optional[str] = None):
        """Load in-memory OSCAL content (str/dict). Returns ``(handle, doc)``."""
        doc = self._ws.loads(content, href=href)
        return self._register(doc), doc

    def new_document(self, model: str, title: str, **kwargs):
        """Create a fresh document from the library template. Returns ``(handle, doc)``."""
        model_cls = _model_class_map().get(model)
        if model_cls is None:
            raise ValueError(f"Unknown OSCAL model {model!r}. Known models: {', '.join(sorted(_model_class_map()))}")
        doc = self._ws.new(model_cls, title, **kwargs)
        return self._register(doc), doc

    # -- lookup / listing / closing ------------------------------------------
    def get(self, handle: str):
        """Return the OSCAL object for ``handle`` or raise :class:`UnknownHandleError`."""
        try:
            return self._by_handle[handle]
        except KeyError:
            raise UnknownHandleError(
                f"No open document with handle {handle!r}. Open handles: "
                f"{', '.join(sorted(self._by_handle)) or '(none)'}"
            )

    def items(self) -> list:
        """Return a list of ``(handle, doc)`` for every open document."""
        with self._lock:
            return list(self._by_handle.items())

    def close(self, handle: str) -> bool:
        """Stop tracking the document and release it from the workspace cache."""
        with self._lock:
            doc = self._by_handle.pop(handle, None)
            if doc is None:
                return False
            self._handle_by_id.pop(id(doc), None)
        self._ws.close(doc)
        return True
