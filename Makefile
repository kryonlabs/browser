.DEFAULT_GOAL := build
ZIRAN ?= ziran
PREFIX ?= $(HOME)/.local
.PHONY: build check test window-test install
build:
	$(ZIRAN) build
check:
	$(ZIRAN) check
# The transport test needs curl; its Python harness only serves fixtures.
test: check
	$(ZIRAN) build --project --root tests --target=c --entry document_test:Main --exe -o build/document-test tests/document_test.zi
	build/document-test/document_test
	$(ZIRAN) build --project --root tests --target=c --entry transport_test:Main --exe -o build/transport-test tests/transport_test.zi
	python3 tests/transport_test.py build/transport-test/transport_test
window-test: build
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS -u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 xvfb-run -a -s '-screen 0 1280x1024x24' env BROWSER_PRIVATE_XVFB=1 python3 tests/window_test.py
install: build
	mkdir -p "$(PREFIX)/bin" "$(PREFIX)/share/applications" "$(PREFIX)/share/icons/hicolor/scalable/apps"
	install -m 755 build/browser-desktop "$(PREFIX)/bin/kryon-browser"
	install -m 644 assets/browser.svg "$(PREFIX)/share/icons/hicolor/scalable/apps/kryon-browser.svg"
	printf '%s\n' '[Desktop Entry]' 'Type=Application' 'Name=Browser' 'Exec=$(PREFIX)/bin/kryon-browser' 'Icon=kryon-browser' 'Terminal=false' 'Categories=Network;WebBrowser;' > "$(PREFIX)/share/applications/kryon-browser.desktop"
