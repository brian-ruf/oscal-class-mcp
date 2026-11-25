# Tailor a profile and resolve it to a catalog

A `Profile` selects and tailors controls from one or more imported catalogs/profiles.

```python
from oscal import Profile

prof = Profile.load("profile.json")

# Each import statement and its resolution status:
for entry in prof.import_list:
    print(entry["href_original"], entry["status"], entry["is_valid"])

# What the profile selects from a given import:
prof.get_import_selection(href="catalog.xml")
prof.set_import_selection(href="catalog.xml", include_all={})  # or with-ids selection
```

## Set parameters and alter controls

```python
prof.set_parameter(param_id="ac-1_prm_1", values=["monthly"])

prof.add_alter(control_id="ac-1")
prof.add_alter_adds(
    control_id="ac-1", position="after", parts=[{"name": "guidance", "prose": "Org-specific guidance."}]
)
prof.add_alter_removes(control_id="ac-1", by_name="guidance")
```

## Merge directives and resolution

```python
prof.set_merge(flat=True)  # or as_is / combine via set_directives(...)
prof.get_directives()

status = prof.resolve()  # builds the resolved catalog
resolved_json = prof.resolve_and_dumps_catalog(format="json", pretty_print=True)
prof.resolve_and_dump_catalog("resolved.json", format="json")

prof.control("ac-1")  # inspect a tailored control (with_history optional)
```

`resolve()` is a full rebuild; call it again after changing selections, parameters, or
alters.
