# Browser

The HTML parser, CSS cascade, document model, layout and product UI belong in
this repository, written in Ziran with Kryon. The Python worker only fetches
documents and resolves URLs; it never renders a page or invokes another browser.
Keep credentials out of logs. Do not run page scripts or submitted forms as
shell commands. Tests and screenshots run on private Xvfb with inherited
display and session variables removed. Never edit dependency checkouts.
