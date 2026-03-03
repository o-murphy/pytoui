# agent.md — Development Instructions for pytoui

You are an AI agent assisting in the development of **pytoui**.  
Your mission is to maintain and evolve an environment where code written for **iOS (Pythonista.ui)** and desktop systems is interchangeable.

---

## 🎯 Strategic Goal: "Dual-Environment Consistency"

### iOS → PC
Code written for **Pythonista** must run on desktop through **pytoui** *as-is*.

### PC → iOS
Code written using **pytoui** must remain compatible with the original Pythonista app.  
Users must never encounter `AttributeError` when moving code back to iOS.

---

# 🏗 Architecture & Compatibility Principles

## 1. The Gold Standard API

- All public classes and methods in `src/ui/` must match the official Pythonista documentation.
- Use stubs in `src/ui/stubgen/` (generated via `inspect` from the original library) as the **single source of truth** for method signatures and properties.
- Public API must remain structurally and behaviorally aligned with Pythonista.

---

## 2. Safe Desktop Extensions

If additional public APIs are required for the desktop runtime:

### Non-Breaking Design
They must not break iOS code.  
If a property exists in `pytoui`, its presence in user code must not cause failures in Pythonista.

Use:
- Shims
- Dynamic attribute injection
- Graceful no-op implementations

### Shims & Fallbacks
Desktop-specific features must:
- Provide empty stub methods when unsupported
- Silently ignore unsupported behavior on iOS
- Never cause `ImportError` or `AttributeError` when code is moved back

---

## 3. Encapsulation of Internal Mechanisms

### Critical Runtime Isolation
Low-level components must be fully hidden:
- Rust libraries (`libosdbuf`, `libwinitrt`)
- Direct framebuffer memory access
- Native window system events

### Private Runtime Methods
Use `_` prefix for methods that:
- Exist only for desktop runtime support
- Are not part of the public Pythonista API

Example:
```python
_update_native_view()
```

---

# 🛠 Technical Development Rules

## Working with `src/ui/`

### Behavioral Fidelity

Classes like:

* `View`
* `Button`
* `Label`

Must closely emulate original Pythonista behavior, including:

* `frame` / `bounds` relationship
* Layout mechanics
* Event dispatch behavior

### Rendering Layer

All drawing must go through:

```
src/osdbuf/__init__.py
```

This module acts as a bridge to the Rust rendering backend.

### Assets

Use fonts from `assets/` to ensure consistent visual output across platforms, independent of system-installed fonts.

---

# 🔁 Workflow

## After Modifying Rust Code

You **must** run:

```
make build
```

This updates `.so` files inside:

```
src/pytoui/
```

## Validation

Test changes using:

```
uv run python -m examples.demo
```

## Cross-Platform Sanity Check

Always ask yourself:

> “Will this crash inside the real Pythonista app on iPad?”

If the answer is **yes** — implement a shim or fallback.

---

# 🚦 Quick Navigation

| Component  | Path              | Compatibility Status                  |
| ---------- | ----------------- | ------------------------------------- |
| Public API | `src/ui/`         | 1:1 with Pythonista + Safe Extensions |
| Stubs      | `src/ui/stubgen/` | Read-only reference                   |
| Rendering  | `src/osdbuf/`     | Internal implementation (hidden)      |
| Examples   | `examples/`       | Must work on both platforms           |

---

# 🛡 Runtime Safety Guarantees

* Never require the user to import anything except:

```python
import ui
```

or

```python
import pytoui.ui as ui
```

* Any desktop-specific functionality must be protected against:

  * `ImportError`
  * `AttributeError`
  * Platform-specific crashes when moved back to iOS

The user experience must feel native and seamless in both environments.

---

# Core Philosophy

pytoui is not a reinterpretation of Pythonista.
It is a compatibility-preserving runtime layer.

When in doubt:

* Favor compatibility over convenience
* Favor shims over breaking changes
* Favor behavioral fidelity over internal elegance
