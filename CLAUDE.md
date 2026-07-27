# Rules for Claude sessions in this repo

## Hard rule: never use API keys — subscription only

- **Never set, request, or use `ANTHROPIC_API_KEY` (or any paid API key) for
  coding, testing, demos, screenshots, or videos in this repo.** All Claude
  usage happens through the user's Claude subscription (the interactive
  session itself), never through pay-per-token API calls.
- Pukaar's `claude` backend (`pukaar/pukaar/backends.py`) exists as
  production code for whoever deploys the project with their own funding.
  It stays dormant here: run everything with `PUKAAR_BACKEND=mock`
  (the default when no key is present). Do not "quick-test" the live
  backend with a key — the mock + the tests are the verification path.
- CI must never carry an API key secret; the suite is designed to pass
  fully offline on the MockBackend.

## Project layout

- `pukaar/` — the working system (FastAPI demo, 99+ tests, `make demo`).
- `research/` — findings, plans, and the Kevin Xu Innovation Challenge
  proposal that the build traces back to.
- Development branch: `claude/street-aid-research-4xqdpu`.
