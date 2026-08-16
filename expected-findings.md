# Expected findings — ground truth

Six deliberate issues in `src/api_client.py`, for validating `eng-agent audit`
and `eng-agent review` output against a known-correct answer. Line numbers are
current as of this file's own commit.

| # | Category | Location | Claim |
|---|---|---|---|
| 1 | Reliability | `get()`, `while True:` loop | No maximum attempt count — retries 429/503 forever instead of eventually raising. |
| 2 | Correctness | `get()`, backoff call | `response.headers["Retry-After"]` is available but never read; the client always uses its own backoff instead of honoring the server. |
| 3 | Input validation | `get()` signature | `timeout` is accepted without checking it's positive. |
| 4 | Requirement/implementation mismatch | `_backoff_delay()` | Docstring and the `max_wait` parameter both promise a cap on backoff between attempts; the cap is never applied. |
| 5 | Test gap | `tests/test_api_client.py` | No test exercises the 429/503 retry path at all — only success (200) and a non-retryable error (404) are covered. |
| 6 | Subtle logic bug | `_is_retryable()` | Uses `is` instead of `==`/`in` to compare integer status codes — flagged by Python itself as a `SyntaxWarning`, and unreliable for status ints not produced as small-int literals (e.g. `int(json_value)`). |

An `eng-agent audit examples/demo-repo` run is expected to surface some
subset of these (bounded to its top-10-findings cap) with real
`path:line`/`symbol` evidence, not paraphrase them as vague prose. The demo
issue in `../demo-issue.md` targets #1, #2, #4, and #5 directly; #3 and #6
are left as `eng-agent audit`/`eng-agent review` targets.
