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
- `lib/` — Native helper crates (Rust) and bindings used by some backends.
	- `lib/osdbuf` and `lib/winitrt` are Rust crates providing low-level support
		for on-screen buffer and runtime glue. These are optional and can be built
		with Cargo if you need native backends.
- Backends: The package supports multiple runtime backends (SDL, winit, etc.).
	Backends live under the package as internal modules (e.g. `_sdlrt`,
	`_winitrt`) and are selected at runtime via the `UI_RT` environment variable.

## Build and install

Requirements and prerequisites:

- Python 3.11 or later, pip and a POSIX shell.
- Recommended: Git for cloning and a C toolchain (build-essential) for native builds.
- Rust toolchain with nightly toolchain (Makefile uses `cargo +nightly` and `-Z build-std`).
- cbindgen (optional, required for `gen-headers`) — installable via cargo or distro package.
- Optional: libsdl2-dev (or other dev packages) if your backend needs system libs.

Example Debian/Ubuntu prerequisites (install Rust via rustup):

```bash
sudo apt update
sudo apt install -y build-essential pkg-config libssl-dev libsdl2-dev
# install rustup (if not installed) and add nightly toolchain:
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup toolchain install nightly
# install cbindgen if you need gen-headers
cargo install cbindgen
```

Makefile targets (actual targets provided in repository):

- make build
  - Builds both native helper crates (lib/osdbuf and lib/winitrt) using `cargo +nightly build --release -Z build-std=std,panic_abort`.
  - Copies resulting shared libraries to `src/pytoui/` as `libosdbuf.so` and `libwinitrt.so`.
- make gen-headers
  - Runs `cbindgen` in each crate to generate C headers (`osdbuf.h`, `winitrt.h`).
- make clean
  - Runs `cargo clean` in the native crates and removes the copied .so files.

Typical workflow using the Makefile:

```bash
# ensure rust nightly and cbindgen are available
# build native libs and copy .so into the Python package
make build

# generate C headers (optional)
make gen-headers

# clean build artifacts
make clean
```

The package uses Hatch/hatchling as the build backend (see `pyproject.toml`).

Use uv to sync dependencies
```bash
uv sync 
```

## Running examples

Small example programs are provided in the `examples/` folder. Example files
include `layouting.py`, `multi_window.py`, and `multitouch.py`.

Run an example by selecting a backend and running the module. For example:

```bash
# use SDL backend and run the layouting example with standard python
UI_RT=sdl python -m examples.layouting

# or if you have a tiny runner script named `uv` in your environment (optional)
UI_RT=sdl uv run -m examples.layouting
```

Adjust `UI_RT` to `winit` or other supported runtimes as available.

## Examples overview

- `examples/layouting.py` — demonstrates layout primitives and view hierarchy.
- `examples/multi_window.py` — simple multi-window sample (backend permitting).
- `examples/multitouch.py` — touches and gesture handling demo.

## Contributing

This project is experimental. If you'd like to contribute:

- Open issues describing use cases or missing features.
- Send pull requests for focused improvements (tests, docs, small features).

## License

This project is licensed under the MIT License. See the LICENSE file in this directory for details.
