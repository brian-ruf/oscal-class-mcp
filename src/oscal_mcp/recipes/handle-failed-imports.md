# Handle failed imports

Imports resolve automatically once a document is minimally valid. Inspect what loaded
and recover from failures without re-loading the whole document.

```python
from oscal import Profile

prof = Profile.load("profile.json")

# Flat list of every import statement and its outcome:
for entry in prof.import_list:
    print(entry["href_original"], entry["status"], entry["is_valid"])

# Only the failures, with structured reasons:
for entry in prof.failed_imports:
    f = entry["failure"]
    print(f"[{f.code.value}] {entry['href_original']} — {f.message}")
```

## Retry a single import with a fallback source

```python
prof.retry_import(
    failed_href="https://old-server.example.com/catalog.xml",
    replacement_href="./local-catalog.xml",
)
prof.resolve_imports()  # force a fresh resolution pass
```

## Walk the full import chain

```python
def visit(entry, depth):
    print("  " * depth, entry["href_original"], entry["status"])


prof.walk_imports(visit, scope="all")  # "successful" | "failed" | "all"
tree = prof.import_tree  # lazily-built recursive dict
```

Note: `allowed-values` and `invalid-type` issues do **not** block import resolution;
missing-required, cardinality, and choice (structural) errors do. Check
`import_blocking_errors` to see what, if anything, is structural.
