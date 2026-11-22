# Browser

A native document browser written in Ziran with Kryon, built from its own HTML
parser, CSS cascade and block layout; classic inline JavaScript runs in a
statically linked, pinned QuickJS engine. Harmony embeds its window;
`kryon-browser` runs it independently. No Chromium or WebKit renders pages.
README.md documents engine limits, build prerequisites and tests.

## Layout

| Path | Contents |
| --- | --- |
| `src/app.zi` | Application entrypoint |
| `src/url.zi` | Address and link resolution |
| `src/transport.zi` | Document loading through Ziran's process channel and curl |
| `src/document.zi` | HTML parsing, CSS cascade and layout |
| `tests/` | Parser/CSS/DOM, transport and window tests |

## Commands

```sh
ziran fetch --locked
make test        # parser/CSS/DOM plus transport tests
make window-test # private-Xvfb window tests
make install
kryon-browser
```

## Pins

- Ziran toolchain: `5db3d3c39425d5dfe4bfe4a84e6f6e2e5a810ad0`
- Kryon: `a66edf19807c221b6f6818e0a54d13c2ad855241`
- QuickJS: official 2026-06-04 archive, verified against a pinned SHA-256.

## Rules

- The HTML parser, CSS cascade, document model, layout and product UI belong
in this repository, written in Ziran with Kryon. Use real Ziran packages and
std modules instead of side programs. Never reintroduce a Python worker or
invoke another browser; Python is allowed only as a test fixture server.
- Keep credentials out of logs. Do not run page scripts or submitted forms as
shell commands.
- Tests and screenshots run on private Xvfb with inherited display and session
variables removed. Never edit dependency checkouts.
