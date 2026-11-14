# Browser

The HTML parser, CSS cascade, document model, layout and product UI belong in
this repository, written in Ziran with Kryon. Use real Ziran packages and std
modules instead of side programs: `src/url.zi` resolves addresses and
`src/transport.zi` loads documents through `std/process_channel_linux` and curl,
as Ziran's std HTTPS GET does. Never reintroduce a Python worker or invoke
another browser; Python is allowed only as a test fixture server.
Keep credentials out of logs. Do not run page scripts or submitted forms as
shell commands. Tests and screenshots run on private Xvfb with inherited
display and session variables removed. Never edit dependency checkouts.
