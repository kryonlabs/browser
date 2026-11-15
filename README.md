# Browser

A native document browser written in Ziran with Kryon, built from its own
HTML parser, CSS cascade and block layout. Its separate repository is
`kryonlabs/browser`. Harmony embeds its window; `kryon-browser` runs it
independently from the desktop. No Chromium or WebKit engine renders pages.
Classic inline JavaScript runs in a statically linked, pinned QuickJS engine.

Enter an HTTP(S) address or local `file:///` URL. Links navigate within the app.
Back and Next restore history and scroll positions. Pages wrap to the window
and scroll independently. Ctrl+L selects the address. Pages load outside the
UI frame: `src/transport.zi` streams curl through Ziran's process channel
and `src/url.zi` resolves links, so the whole browser is Ziran plus curl.

The initial engine supports headings, paragraphs, lists, links, preformatted
text, image descriptions and malformed HTML recovery. Embedded/inline CSS
supports element/class/ID selectors, per-property specificity, inheritance,
colors, backgrounds, font sizes, margins, padding, width/max-width and
display:none. Colors include short/full hex and basic named colors.

Classic inline scripts execute in source order. The deliberately small DOM
surface includes `document.getElementById`, `document.querySelector` (the first
`#id`, `.class`, or tag match), element `textContent`, and `document.title`.
Each navigation gets a fresh QuickJS runtime with a 16 MiB engine-memory limit,
a 256 KiB stack limit, and a 100 ms total deadline. Exceptions are contained
and later inline scripts are still attempted. QuickJS's `std` and `os` modules
are not loaded, and pages get no file, process, shell, or network host API. The
official QuickJS 2026-06-04 source archive is verified against a pinned SHA-256
before it is built.

QuickJS currently runs inside the browser process rather than an OS-isolated
renderer process. The engine limits and absent host APIs reduce page authority,
but they are not a complete operating-system sandbox.

This is a basic document engine. Inline elements currently participate in block
flow. External and module scripts, event handlers, timers, an asynchronous event
loop, forms, external stylesheets, decoded images, flexbox, grid, cookies and
authentication remain future work. The DOM is a bounded snapshot, not a complete
live web DOM. Limits are 512 KiB of input, 240 tree nodes, and 32 inline scripts,
with a visible notice when the tree preview is truncated.

## Build and verify

Install Ziran, SDL2, Cairo, FreeType, X11, curl, a C compiler and xz; Python 3
only serves test fixtures. Dependencies and compiler are pinned in
`ziran.lock`; local development uses ignored package overrides.

```sh
ziran fetch --locked
make test
make window-test
make install
kryon-browser
```

Parser/CSS/DOM tests execute the production Ziran and QuickJS integration.
Transport tests use disposable files. Window tests scrub inherited
display/session variables and start private Xvfb, then exercise address input,
HTML/CSS rendering, script mutations and limits, relative links, history,
scrolling and a narrow window. Screenshots are written under
`build/screenshots/`.
