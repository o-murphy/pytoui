"""Hatchling custom build hook.

Compiles Rust cdylibs (osdbuf, winitrt) for the target platform/arch and
places the resulting shared libraries in src/pytoui/ before the wheel is
assembled.  Detects the Rust target triple automatically so it works
correctly inside every cibuildwheel container (manylinux, musllinux,
macOS arm64/x86_64/universal2, Windows AMD64/x86/ARM64).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

ROOT = Path(__file__).resolve().parent.parent
DEPS_DIR = ROOT / "deps"
OUT_DIR = ROOT / "src" / "pytoui"
CRATES = ["osdbuf", "winitrt"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(*cmd: str | Path, cwd: Path | None = None, env: dict | None = None) -> None:
    print(f"  $ {' '.join(str(c) for c in cmd)}", flush=True)
    merged_env = None
    if env:
        merged_env = os.environ.copy()
        merged_env.update(env)
    subprocess.run([str(c) for c in cmd], check=True, cwd=cwd, env=merged_env)


def _find_tool(name: str) -> str:
    """Locate a binary in PATH or the default cargo install directory."""
    found = shutil.which(name)
    if found:
        return found
    home = Path.home()
    for ext in ("", ".exe"):
        candidate = home / ".cargo" / "bin" / f"{name}{ext}"
        if candidate.exists():
            return str(candidate)
    raise RuntimeError(
        f"'{name}' not found. Install Rust via https://rustup.rs "
        f"and ensure ~/.cargo/bin is in PATH."
    )


# ---------------------------------------------------------------------------
# Library filename helpers
# ---------------------------------------------------------------------------


def _lib_file_for_target(crate: str, target: str) -> str:
    """Filename produced by Cargo inside target/<triple>/release/."""
    if "windows" in target:
        return f"{crate}.dll"
    if "darwin" in target:
        return f"lib{crate}.dylib"
    return f"lib{crate}.so"


def _dest_file(crate: str) -> str:
    """Destination filename placed in src/pytoui/."""
    if sys.platform == "win32":
        return f"{crate}.dll"
    if sys.platform == "darwin":
        return f"lib{crate}.dylib"
    return f"lib{crate}.so"


# ---------------------------------------------------------------------------
# Target detection
# ---------------------------------------------------------------------------


def _detect_targets() -> list[str]:
    """Return Rust target triple(s) for the current build environment.

    Returns two triples only for macOS universal2; everything else is a
    single-element list.
    """
    plat = sysconfig.get_platform()  # e.g. linux-x86_64, macosx-14.0-arm64, win-amd64

    # ── macOS ────────────────────────────────────────────────────────────
    if sys.platform == "darwin":
        if "universal2" in plat:
            return ["x86_64-apple-darwin", "aarch64-apple-darwin"]
        if "arm64" in plat:
            return ["aarch64-apple-darwin"]
        return ["x86_64-apple-darwin"]

    # ── Windows ──────────────────────────────────────────────────────────
    if sys.platform == "win32":
        # sysconfig.get_platform() is reliable even for 32-bit Python on 64-bit OS
        table = {
            "win-amd64": "x86_64-pc-windows-msvc",
            "win32": "i686-pc-windows-msvc",
            "win-arm64": "aarch64-pc-windows-msvc",
        }
        target = table.get(plat)
        if not target:
            raise RuntimeError(f"Unsupported Windows platform: {plat!r}")
        return [target]

    # ── Linux ────────────────────────────────────────────────────────────
    if sys.platform.startswith("linux"):
        # Use the Python interpreter's own platform tag, not platform.machine().
        # platform.machine() returns the HOST kernel arch (always x86_64 on an
        # x86_64 host), so inside a 32-bit manylinux_i686 container it returns
        # "x86_64" instead of "i686" — causing the Rust code to be compiled for
        # x86_64 and auditwheel to retag the wheel, producing duplicate filenames.
        # sysconfig.get_platform() reflects the INTERPRETER's arch (correct).
        arch = plat[len("linux-") :].lower()  # "linux-i686" → "i686"

        # Detect musl via cibuildwheel's env var or ldd output
        is_musl = "musl" in os.environ.get("AUDITWHEEL_PLAT", "").lower()
        if not is_musl:
            try:
                r = subprocess.run(
                    ["ldd", "--version"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                is_musl = "musl" in (r.stdout + r.stderr).lower()
            except FileNotFoundError:
                pass

        libc = "musl" if is_musl else "gnu"

        arch_map: dict[str, str] = {
            "x86_64": f"x86_64-unknown-linux-{libc}",
            "i686": f"i686-unknown-linux-{libc}",
            "i386": f"i686-unknown-linux-{libc}",
            "aarch64": f"aarch64-unknown-linux-{libc}",
            "arm64": f"aarch64-unknown-linux-{libc}",
            "armv7l": (
                "armv7-unknown-linux-musleabihf"
                if is_musl
                else "armv7-unknown-linux-gnueabihf"
            ),
            # armv8l = 32-bit userland on AArch64 hardware (e.g. Raspberry Pi OS)
            "armv8l": (
                "armv7-unknown-linux-musleabihf"
                if is_musl
                else "armv7-unknown-linux-gnueabihf"
            ),
        }
        target = arch_map.get(arch)
        if not target:
            raise RuntimeError(f"Unsupported Linux arch: {arch!r}")
        return [target]

    raise RuntimeError(f"Unsupported platform: {sys.platform!r}")


# ---------------------------------------------------------------------------
# Toolchain management
# ---------------------------------------------------------------------------


def _ensure_targets(targets: list[str]) -> None:
    """Register Rust targets via rustup (needed for cross-compilation).

    rust-src and the nightly toolchain are handled by rust-toolchain.toml.
    build-std is handled by [unstable] in .cargo/config.toml.
    """
    try:
        rustup = _find_tool("rustup")
    except RuntimeError:
        return
    for target in targets:
        _run(rustup, "target", "add", "--toolchain", "nightly", target)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def _build_crate(crate: str, target: str) -> Path:
    """Compile one cdylib for *target* and return the output path.

    Toolchain (nightly) comes from rust-toolchain.toml.
    build-std and musl rustflags come from .cargo/config.toml.
    """
    cargo = _find_tool("cargo")
    crate_dir = DEPS_DIR / crate
    _run(cargo, "build", "--release", f"--target={target}", cwd=crate_dir)
    lib = _lib_file_for_target(crate, target)
    return crate_dir / "target" / target / "release" / lib


def _build_all() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    targets = _detect_targets()
    print(f"==> Rust target(s): {targets}", flush=True)

    _ensure_targets(targets)

    for crate in CRATES:
        dest = OUT_DIR / _dest_file(crate)

        if len(targets) == 2 and sys.platform == "darwin":
            # macOS universal2: compile both slices then lipo them together
            libs = [_build_crate(crate, t) for t in targets]
            _run("lipo", "-create", "-output", dest, *libs)
            print(f"==> lipo -> {dest}", flush=True)
        else:
            src = _build_crate(crate, targets[0])
            shutil.copy2(src, dest)
            print(f"==> {src.name} -> {dest}", flush=True)


# ---------------------------------------------------------------------------
# Hatchling hook
# ---------------------------------------------------------------------------


class CustomBuildHook(BuildHookInterface):
    def initialize(self, _version, build_data):
        _env = os.environ.get("PURE", "").strip().lower()
        pure = _env in ("1", "true", "yes")

        if self.target_name == "wheel":
            if not pure:
                print("==> Pre-build hook: building cdylibs for wheel", flush=True)
                _build_all()

                plat = sysconfig.get_platform().replace("-", "_").replace(".", "_")
                py = f"cp{sys.version_info.major}{sys.version_info.minor}"
                is_free_threaded = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))
                abi = py + ("t" if is_free_threaded else "")
                build_data["pure-python"] = False
                build_data["tag"] = f"{py}-{abi}-{plat}"
            else:
                print(
                    f"==> Pre-build hook: skip native build "
                    f"(pure=True, platform={sys.platform})",
                    flush=True,
                )
        else:
            print(
                f"==> Pre-build hook: skip native build ({pure=}, {sys.platform=})",
                flush=True,
            )
