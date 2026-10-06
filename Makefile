.DEFAULT_GOAL := build
ZIRAN ?= ziran
PREFIX ?= $(HOME)/.local
.PHONY: build check test window-test install
build:
	$(ZIRAN) build
	cp scripts/fetch.py scripts/start.html build/
check:
	$(ZIRAN) check
test: check
	python3 -m unittest discover -s tests -v
	$(ZIRAN) build --project --root tests --target=c --entry document_test:Main --exe -o build/document-test tests/document_test.zi
	build/document-test/document_test
window-test: build
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS -u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 xvfb-run -a -s '-screen 0 1280x1024x24' env BROWSER_PRIVATE_XVFB=1 python3 tests/window_test.py
install: build
	mkdir -p "$(PREFIX)/bin" "$(PREFIX)/lib/browser" "$(PREFIX)/share/applications" "$(PREFIX)/share/icons/hicolor/scalable/apps"
	install -m 755 build/browser-desktop "$(PREFIX)/lib/browser/browser-desktop"
	install -m 644 scripts/fetch.py scripts/start.html "$(PREFIX)/lib/browser/"
	install -m 644 assets/browser.svg "$(PREFIX)/share/icons/hicolor/scalable/apps/kryon-browser.svg"
	printf '%s\n' '#!/bin/sh' 'exec "$(PREFIX)/lib/browser/browser-desktop" "$$@"' > "$(PREFIX)/bin/kryon-browser"
	chmod 755 "$(PREFIX)/bin/kryon-browser"
	printf '%s\n' '[Desktop Entry]' 'Type=Application' 'Name=Browser' 'Exec=$(PREFIX)/bin/kryon-browser' 'Icon=kryon-browser' 'Terminal=false' 'Categories=Network;WebBrowser;' > "$(PREFIX)/share/applications/kryon-browser.desktop"
