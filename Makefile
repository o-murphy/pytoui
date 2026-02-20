CARGO       = cargo +nightly
CARGO_FLAGS = --release -Z build-std=std,panic_abort

OUT_DIR     = src/pytoui
OUT_SO_OSDLIB      = $(OUT_DIR)/libosdbuf.so
OUT_SO_WINITRT      = $(OUT_DIR)/libwinitrt.so

.PHONY: build clean eject-device push-device gen-headers

build:
	@echo "==> Building osdbuf cdylib (host)..."
	cd lib/osdbuf && $(CARGO) build $(CARGO_FLAGS)
	@mkdir -p $(OUT_DIR)
	cp lib/osdbuf/target/release/libosdbuf.so $(OUT_SO_OSDLIB)
	@echo "==> Done."

	@echo "==> Building winitrt cdylib (host)..."
	cd lib/winitrt && $(CARGO) build $(CARGO_FLAGS)
	@mkdir -p $(OUT_DIR)
	cp lib/winitrt/target/release/libwinitrt.so $(OUT_SO_WINITRT)
	@echo "==> Done."

eject-device:
	ar-sign --dev --eject

gen-headers:
	@echo "==> Generating C header..."
	cd lib/osdbuf && cbindgen --config cbindgen.toml --output osdbuf.h
	cd lib/winitrt && cbindgen --config cbindgen.toml --output winitrt.h

clean:
	cd lib/osdbuf && cargo clean
	cd lib/winitrt && cargo clean
	rm -f $(OUT_SO_OSDLIB)
	rm -f $(OUT_SO_WINITRT)
