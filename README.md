# Demo Repo

A small, synthetic Python project used to exercise Engineering Agent end-to-end
(`eng-agent issue`, `eng-agent review`, `eng-agent audit`) without touching a
real codebase. It has one module, `src/api_client.py`, with six deliberate
engineering issues (see comments marked `BUG(n):` in the source) and a test
suite that passes today — precisely because it doesn't cover any of them.

This is not a real HTTP client. Nothing here talks to the network; `_send`
is a seam meant to be monkeypatched/mocked in tests.

## Run its own tests

```bash
python3 -m pytest examples/demo-repo/tests
```

## The flagship demo issue

See [`../demo-issue.md`](../demo-issue.md).
