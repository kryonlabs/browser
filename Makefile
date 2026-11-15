.DEFAULT_GOAL := build
ZIRAN ?= ziran
PREFIX ?= $(HOME)/.local
QUICKJS_VERSION := 2026-06-04
QUICKJS_SHA256 := b376e839b322978313d929fd20663b11ba58b75df5a46c126dd19ea2fa70ad2a
QUICKJS_TARBALL := build/quickjs-$(QUICKJS_VERSION).tar.xz
QUICKJS_SOURCE := build/quickjs-$(QUICKJS_VERSION)
QUICKJS_STAMP := $(QUICKJS_SOURCE)/.browser-extracted
QUICKJS_BUILD := build/quickjs
QUICKJS_ARCHIVE := $(QUICKJS_BUILD)/libbrowser_script.a
QUICKJS_OBJECTS := $(QUICKJS_BUILD)/quickjs.o $(QUICKJS_BUILD)/dtoa.o $(QUICKJS_BUILD)/libregexp.o $(QUICKJS_BUILD)/libunicode.o $(QUICKJS_BUILD)/cutils.o $(QUICKJS_BUILD)/script_bridge.o
QUICKJS_CFLAGS := -std=gnu11 -O2 -fPIC -fwrapv -D_GNU_SOURCE -DCONFIG_VERSION=\"$(QUICKJS_VERSION)\" -I$(QUICKJS_SOURCE)
.PHONY: build check test window-test install quickjs
build: $(QUICKJS_ARCHIVE)
	$(ZIRAN) build
check: $(QUICKJS_ARCHIVE)
	$(ZIRAN) check
quickjs: $(QUICKJS_ARCHIVE)
$(QUICKJS_TARBALL):
	mkdir -p build
	curl -fL --retry 3 -o "$@.part" "https://bellard.org/quickjs/quickjs-$(QUICKJS_VERSION).tar.xz"
	printf '%s  %s\n' "$(QUICKJS_SHA256)" "$@.part" | sha256sum -c -
	mv "$@.part" "$@"
$(QUICKJS_STAMP): $(QUICKJS_TARBALL)
	tar -xf "$<" -C build
	touch "$@"
$(QUICKJS_SOURCE)/quickjs.c: $(QUICKJS_STAMP)
$(QUICKJS_BUILD)/%.o: $(QUICKJS_SOURCE)/%.c $(QUICKJS_SOURCE)/quickjs.h
	mkdir -p $(QUICKJS_BUILD)
	$(CC) $(QUICKJS_CFLAGS) -c "$<" -o "$@"
$(QUICKJS_BUILD)/script_bridge.o: src/script_bridge.c src/script_bridge.h $(QUICKJS_SOURCE)/quickjs.h
	mkdir -p $(QUICKJS_BUILD)
	$(CC) $(QUICKJS_CFLAGS) -c "$<" -o "$@"
$(QUICKJS_ARCHIVE): $(QUICKJS_OBJECTS)
	$(AR) rcs "$@" $^
	cp "$(QUICKJS_SOURCE)/LICENSE" "$(QUICKJS_BUILD)/LICENSE"
test: check $(QUICKJS_ARCHIVE)
	$(CC) -std=c11 -O2 -Isrc tests/script_bridge_test.c "$(QUICKJS_ARCHIVE)" -lm -ldl -lpthread -o build/script-bridge-test
	build/script-bridge-test
	LDLIBS="$(CURDIR)/$(QUICKJS_ARCHIVE) -lm -ldl -lpthread" $(ZIRAN) build --project --root tests --target=c --entry document_test:Main --exe -o build/document-test tests/document_test.zi
	build/document-test/document_test
	# The transport test needs curl; its Python harness only serves fixtures.
	$(ZIRAN) build --project --root tests --target=c --entry transport_test:Main --exe -o build/transport-test tests/transport_test.zi
	python3 tests/transport_test.py build/transport-test/transport_test
window-test: build
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS -u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 xvfb-run -a -s '-screen 0 1280x1024x24' env BROWSER_PRIVATE_XVFB=1 python3 tests/window_test.py
install: build
	mkdir -p "$(PREFIX)/bin" "$(PREFIX)/share/applications" "$(PREFIX)/share/icons/hicolor/scalable/apps" "$(PREFIX)/share/licenses/kryon-browser"
	install -m 755 build/browser-desktop "$(PREFIX)/bin/kryon-browser"
	install -m 644 "$(QUICKJS_BUILD)/LICENSE" "$(PREFIX)/share/licenses/kryon-browser/QuickJS"
	install -m 644 assets/browser.svg "$(PREFIX)/share/icons/hicolor/scalable/apps/kryon-browser.svg"
	printf '%s\n' '[Desktop Entry]' 'Type=Application' 'Name=Browser' 'Exec=$(PREFIX)/bin/kryon-browser' 'Icon=kryon-browser' 'Terminal=false' 'Categories=Network;WebBrowser;' > "$(PREFIX)/share/applications/kryon-browser.desktop"
