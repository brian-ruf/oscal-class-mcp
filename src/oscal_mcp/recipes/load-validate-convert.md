# Load, validate, and convert an OSCAL document

The base `OSCAL` class auto-detects the model; use a model class (`Catalog`, `Profile`,
…) when you know it in advance. XML/JSON/YAML all load the same way.

```python
from oscal import OSCAL

doc = OSCAL.load("catalog.xml")  # local path (str, Path, or file-like)
# doc = OSCAL.loads(text, href="mem")  # in-memory string or dict
# doc = OSCAL.acquire("https://…")     # URI / remote, with optional fallback list

print(doc.model)  # e.g. "catalog"
print(doc.oscal_version)  # e.g. "v1.1.3"
```

## Check validity

Loading runs validation automatically. Inspect the tiered results:

```python
if doc.is_valid:  # L2: structure + data-types + allowed-values + cardinality
    print("valid")
elif doc.is_minimally_valid:  # structurally sound; may have allowed-value/type issues
    print("minimally valid")

print(doc.validation_status)  # per-phase dict
for err in doc.validation_errors:
    print(err["error-type"], err["location"], err["identifier"], err["value"])

doc.validate_full()  # L3: scoped constraints (sets is_fully_compliant)
```

`bool(doc)` is `True` when `is_valid` is `True`, so `if doc:` works as a validity gate.

## Convert formats

Serialization always emits canonical NIST metaschema key/element order.

```python
doc.dumps(format="json", pretty_print=True)  # -> str
doc.dumps(format="xml", pretty_print=True)
doc.dumps(format="yaml")

doc.dump("out.json", format="json", pretty_print=True)  # -> writes file, returns True
doc.dump()  # back to original path+format

doc.json  # convenience properties (pretty, canonical)
doc.xml
doc.yaml
```
