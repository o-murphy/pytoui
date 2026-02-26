CARGO       = cargo +nightly
CARGO_FLAGS = --release -Z build-std=std,panic_abort

OUT_DIR = src/pytoui

# Detect library extension and prefix per platform
ifeq ($(OS), Windows_NT)
  LIB_EXT    = dll
  LIB_PREFIX =
else
  UNAME := $(shell uname -s)
  ifeq ($(UNAME), Darwin)
    LIB_EXT    = dylib
  else
    LIB_EXT    = so
  endif
  LIB_PREFIX = lib
endif

OUT_OSDLIB  = $(OUT_DIR)/$(LIB_PREFIX)osdbuf.$(LIB_EXT)
OUT_WINITRT = $(OUT_DIR)/$(LIB_PREFIX)winitrt.$(LIB_EXT)

.PHONY: build clean gen-headers

build:
	@echo "==> Building osdbuf cdylib (host)..."
	cd deps/osdbuf && $(CARGO) build $(CARGO_FLAGS)
	@mkdir -p $(OUT_DIR)
	cp deps/osdbuf/target/release/$(LIB_PREFIX)osdbuf.$(LIB_EXT) $(OUT_OSDLIB)
	@echo "==> Done."

	@echo "==> Building winitrt cdylib (host)..."
	cd deps/winitrt && $(CARGO) build $(CARGO_FLAGS)
	@mkdir -p $(OUT_DIR)
	cp deps/winitrt/target/release/$(LIB_PREFIX)winitrt.$(LIB_EXT) $(OUT_WINITRT)
	@echo "==> Done."

gen-headers:
	@echo "==> Generating C headers..."
	cd deps/osdbuf && cbindgen --config cbindgen.toml --output osdbuf.h
	cd deps/winitrt && cbindgen --config cbindgen.toml --output winitrt.h

clean:
	cd deps/osdbuf && cargo clean
	cd deps/winitrt && cargo clean
	rm -f $(OUT_OSDLIB) $(OUT_WINITRT)
