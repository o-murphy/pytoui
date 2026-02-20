CARGO       = cargo +nightly
CARGO_FLAGS = --release -Z build-std=std,panic_abort

OUT_DIR_OSDLIB     = src/osdbuf
OUT_SO_OSDLIB      = $(OUT_DIR_OSDLIB)/libosdbuf.so

OUT_DIR_WINITRT     = src/winitrt
OUT_SO_WINITRT      = $(OUT_DIR_WINITRT)/libwinitrt.so

MUSL_TOOLCHAIN     = mips32el--musl--stable-2025.08-1
MUSL_TOOLCHAIN_URL = https://toolchains.bootlin.com/downloads/releases/toolchains/mips32el/tarballs/$(MUSL_TOOLCHAIN).tar.xz
GNU_TOOLCHAIN      = mips32el--glibc--stable-2018.11-1
GNU_TOOLCHAIN_URL  = https://toolchains.bootlin.com/downloads/releases/toolchains/mips32el/tarballs/$(GNU_TOOLCHAIN).tar.xz

.PHONY: host clean eject-device push-device gen-headers

host:
	@echo "==> Building osdbuf cdylib (host)..."
	cd osdbuf && $(CARGO) build $(CARGO_FLAGS)
	@mkdir -p $(OUT_DIR_OSDLIB)
	cp osdbuf/target/release/libosdbuf.so $(OUT_SO_OSDLIB)
	@echo "==> Done."

	@echo "==> Building winitrt cdylib (host)..."
	cd winitrt && $(CARGO) build $(CARGO_FLAGS)
	@mkdir -p $(OUT_DIR_WINITRT)
	cp winitrt/target/release/libwinitrt.so $(OUT_SO_WINITRT)
	@echo "==> Done."

eject-device:
	ar-sign --dev --eject

gen-headers:
	@echo "==> Generating C header..."
	cd osdbuf && cbindgen --config cbindgen.toml --output osdbuf.h
	cd winitrt && cbindgen --config cbindgen.toml --output winitrt.h

clean:
	cd osdbuf && cargo clean
	cd winitrt && cargo clean
	rm -f $(OUT_SO_OSDLIB)
	rm -f $(OUT_SO_WINITRT)
