# pytoui

Lightweight Python UI runtime inspired by Pythonista.ui — early-stage project.

This repository implements a small GUI toolkit and runtime that aims to be
conceptually compatible with Pythonista.ui while running on desktop systems.
It is an early experimental project: APIs are provisional and the implementation
is incomplete. Contributions and feedback are welcome.

## Status

- Early-stage: APIs and internals may change without notice.
- Focused on compatibility with Pythonista.ui idioms (views, controls, layout).

## Compatibility

The goal is to provide a familiar API and layout model for code written for
Pythonista.ui so porting small UI scripts should be straightforward. Not all
features are implemented yet; check the examples for the current surface.

## Architecture

- `src/pytoui` — Pure-Python package exposing the public UI API and widgets.
	- `pytoui.ui` contains widget implementations such as labels, buttons,
		images, sliders, and views.
	- `_runtime` modules (internal) select and host platform backends.
- `assets/` — Bundled font assets (Inter, Roboto). Included in wheels as `pytoui/assets/`.
- Native libraries — Rust crates compiled to `.so` files placed in `src/pytoui/`:
	- `libosdbuf.so` — on-screen framebuffer drawing via tiny-skia and fontdue.
	- `libwinitrt.so` — winit-based windowing runtime.
- Backends: Multiple runtime backends are supported (SDL, winit, framebuffer).
	Selected at runtime via the `UI_RT` environment variable
	(`sdl`, `winit`, `fb`; default: `winit`).

## Build and install

### Quick start on Pythonista

Execute this code in Pythonista console to install
```python
import requests as r; exec(r.get('https://raw.githubusercontent.com/o-murphy/pytoui/refs/heads/main/scripts/get_pytoui.py').content)
```

Execute this code in Pythonista console to remove
```python
import requests as r; exec(r.get('https://raw.githubusercontent.com/o-murphy/pytoui/refs/heads/main/scripts/prune_pytoui.py').content)
```

### Prerequisites

- Python 3.10 or later.
- Rust toolchain with nightly channel (builds use `cargo +nightly` and `-Z build-std`).
- `cbindgen` — optional, required for `make gen-headers`.
- `libsdl2-dev` — required for the SDL backend.

Example (Debian/Ubuntu):

```bash
sudo apt install -y build-essential pkg-config libssl-dev libsdl2-dev
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup toolchain install nightly
cargo install cbindgen   # optional
```

### Development setup

```bash
# 1. Compile native libraries (Rust → .so in src/pytoui/)
make build

# 2. Sync Python dependencies
uv sync

# 3. Install pre-commit hooks
uv run pre-commit install
```

`uv sync` only installs Python dependencies — it does **not** compile the native libs.
Run `make build` once after cloning, and again after changes to the Rust crates.

### Makefile targets

| Target             | Description                                                      |
| ------------------ | ---------------------------------------------------------------- |
| `make build`       | Compile both Rust crates and copy `.so` files into `src/pytoui/` |
| `make gen-headers` | Generate C headers via cbindgen (optional)                       |
| `make clean`       | Remove build artifacts and `.so` files                           |

### Building a wheel

```bash
# Native wheel (compiles .so via make, platform-specific tag)
uv build

# Pure-Python wheel (no compilation, py3-none-any)
PURE=1 uv build
```

## Running examples

Small example programs are in the `examples/` folder:

```bash
UI_RT=sdl uv run python -m examples.demo
UI_RT=winit uv run python -m examples.demo
```

## Examples overview

- `examples/demo.py` — layout primitives and view hierarchy.
- `examples/components/` — individual widget demos.
- `examples/custom/` — custom view examples.
- `examples/flex.py` — flex layout demo.
- `examples/text.py` — text rendering demo.
- `examples/mouse_wheel.py` — mouse wheel / scroll demo.
- `examples/multi_window.py` — multi-window sample.
- `examples/multitouch.py` — touch and gesture handling.

## Contributing

This project is experimental. If you'd like to contribute:

- Open issues describing use cases or missing features.
- Send pull requests for focused improvements (tests, docs, small features).

## License

This project is licensed under the MIT License. See the LICENSE file for details.
