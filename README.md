# Browser

A native document browser written in Ziran with Kryon, built from its own
HTML parser, CSS cascade and block layout. Its separate repository is
`kryonlabs/browser`. Harmony embeds its window; `kryon-browser` runs it
independently from the desktop. No Chromium or WebKit engine renders pages.

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

This is a basic document engine. Inline elements currently participate in block
flow. JavaScript, forms, external stylesheets, decoded images, flexbox, grid,
cookies and authentication remain future work. Limits are 512 KiB of input and
240 tree nodes, with a visible notice when the tree preview is truncated.

## Build and verify

Install Ziran, SDL2, Cairo, FreeType, X11 and curl; Python 3 only serves test
fixtures. Dependencies and compiler
are pinned in `ziran.lock`; local development uses ignored package overrides.

```sh
ziran fetch --locked
make test
make window-test
make install
kryon-browser
```

Parser/CSS tests execute the production Ziran engine. Transport tests use
disposable files. Window tests scrub inherited display/session variables and
start private Xvfb, then exercise address input, HTML/CSS rendering, relative
links, history, scrolling and a narrow window. Screenshots are written under
`build/screenshots/`.
