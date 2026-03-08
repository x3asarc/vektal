---
name: defense-in-depth
description: Validate at every layer data passes through to make bugs structurally impossible. Use when implementing any function that processes external input, mutates state, or triggers side effects.
---

# Defense-in-Depth

## Core Principle

**Validate data at every layer it passes through. Don't trust that the caller validated it.**

Bugs are impossible when invalid data is caught at the earliest possible layer AND re-validated at every layer it passes through. A single validation point is a single point of failure.

## The Four Layers

### Layer 1: Entry Point Validation
At the API boundary — reject obviously invalid data before it enters the system.

```python
def process_order(order_id: str, items: list):
    assert order_id and order_id.startswith("ord_"), f"Invalid order_id: {order_id}"
    assert items, "Order must have at least one item"
```

### Layer 2: Business Logic Validation
Inside operations — ensure data makes sense for THIS specific operation.

```python
def apply_discount(order, discount_pct: float):
    assert 0 < discount_pct <= 100, f"Discount {discount_pct}% out of range"
    assert order.status == "pending", f"Can't discount {order.status} order"
```

### Layer 3: Environment Guards
Prevent dangerous operations based on context.

```python
def sync_to_production(data):
    assert os.getenv("ENV") == "production", "Must be on production env"
    assert not IS_TESTING, "Refusing production sync during tests"
```

### Layer 4: Debug Instrumentation
Log enough context for forensic analysis if something slips through.

```python
import logging
log.debug("process_order called", extra={"order_id": order_id, "item_count": len(items)})
```

## Process

1. Trace the data flow for the function you're writing
2. Identify every layer the data passes through
3. Add a validation checkpoint at each layer
4. Add debug logging at the entry and exit of each layer
5. Test that bypasses are caught: pass invalid data to Layer 2 directly (skipping Layer 1)

## Example: Preventing `git init` in Wrong Directory

```python
def init_project(path: str):
    # Layer 1: entry validation
    assert path and os.path.isabs(path), f"Path must be absolute: {path}"
    
    # Layer 2: business logic
    assert not os.path.exists(os.path.join(path, ".git")), f"Already a git repo: {path}"
    
    # Layer 3: environment guard
    assert path.startswith(PROJECTS_ROOT), f"Path outside projects dir: {path}"
    
    # Layer 4: instrumentation
    log.info(f"init_project: {path}")
    subprocess.run(["git", "init", path], check=True)
```

## Output

Report each validation added:
```
Layer 1 (entry): [what was validated]
Layer 2 (business): [what was validated]
Layer 3 (environment): [what was validated]
Layer 4 (instrumentation): [what was logged]
Bypasses tested: [yes/no + how]
```
