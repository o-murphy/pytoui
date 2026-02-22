CARGO       = cargo +nightly
CARGO_FLAGS = --release -Z build-std=std,panic_abort

OUT_DIR     = src/pytoui
OUT_SO_OSDLIB      = $(OUT_DIR)/libosdbuf.so
OUT_SO_WINITRT      = $(OUT_DIR)/libwinitrt.so

.PHONY: build clean gen-headers

build:
	@echo "==> Building osdbuf cdylib (host)..."
	cd deps/osdbuf && $(CARGO) build $(CARGO_FLAGS)
	@mkdir -p $(OUT_DIR)
	cp deps/osdbuf/target/release/libosdbuf.so $(OUT_SO_OSDLIB)
	@echo "==> Done."

	@echo "==> Building winitrt cdylib (host)..."
	cd deps/winitrt && $(CARGO) build $(CARGO_FLAGS)
	@mkdir -p $(OUT_DIR)
	cp deps/winitrt/target/release/libwinitrt.so $(OUT_SO_WINITRT)
	@echo "==> Done."

gen-headers:
	@echo "==> Generating C header..."
	cd deps/osdbuf && cbindgen --config cbindgen.toml --output osdbuf.h
	cd deps/winitrt && cbindgen --config cbindgen.toml --output winitrt.h

clean:
	cd deps/osdbuf && cargo clean
	cd deps/winitrt && cargo clean
	rm -f $(OUT_SO_OSDLIB)
	rm -f $(OUT_SO_WINITRT)
