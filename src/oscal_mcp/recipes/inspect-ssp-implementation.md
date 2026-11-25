# Inspect an SSP or component definition

`SSP` (system-security-plan) and `ComponentDefinition` describe how controls are
implemented. Both resolve their single/many imports automatically when valid.

```python
from oscal import SSP, ComponentDefinition

ssp = SSP.load("ssp.json")

# Components and leveraged authorizations by uuid:
ssp.component(uuid="11111111-1111-1111-1111-111111111111")
ssp.leveraged_authorization(uuid="…")

# A control's implemented requirement (optionally with the resolved control text):
ssp.control("ac-1", with_control=True)
```

## Author implementation content

Mutation requires `is_editable`.

```python
ssp.append_component(
    component_type="software",
    component_title="Web Server",
    component_description="nginx reverse proxy",
    op_status="operational",
)
ir = ssp.append_impl_requirement(control_id="ac-1")
ssp.add_by_component(
    implemented_requirement_uuid=ir["uuid"],
    component_uuid="…",
    description="How this component satisfies ac-1.",
)
```

## Component definitions

```python
cdef = ComponentDefinition.load("component-definition.json")
cdef.component(uuid="…")
cdef.capability(uuid="…")
cdef.control_implementation(uuid="…")
```
