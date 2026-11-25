# Create a catalog and add controls

Create documents from the built-in template with `.new()` on a model class (never
instantiate the classes directly). `.new()` stamps a fresh root `uuid` and
`last-modified`.

```python
from oscal import Catalog

cat = Catalog.new(
    title="My Catalog",
    version="1.0.0",
    published="2026-01-01T00:00:00Z",  # optional ISO-8601
)
```

## Read metadata from live content

The cached `.title` / `.version` attributes can lag after `.new()` or a mutation; read
live values with a query:

```python
cat.json_query_one("/*/metadata/title")  # JSON-key syntax, no index needed
cat.query_one("/*/metadata/title")  # XML-element syntax, needs metaschema index
```

## Add groups and controls

Mutation requires `is_editable` (valid, local, not read-only). Methods return a safe
copy of the created node; edit further via another call, not by mutating the copy.

```python
cat.create_control_group(parent_id="", id="ac", title="Access Control")
cat.create_control(
    parent_id="ac",  # "" = top level
    id="ac-1",
    title="Policy and Procedures",
    statements=["The organization develops …"],
    guidance="Supplemental guidance …",
)
cat.add_part(parent_id="ac-1", name="objective", prose="Determine if …")

cat.get_control_by_id("ac-1")  # detached copy (optional depth=N to prune children)
cat.get_control_list()  # all control ids
```

Re-validate after edits and save:

```python
cat.validate()
cat.dump("my-catalog.json", format="json", pretty_print=True)
```
