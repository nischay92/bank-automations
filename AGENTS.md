# Codex handoff

This repository is a take-home assessment for a computer-use automation system. Read `README.md`, `REPORT.md`, and `evidence/README.md` before changing the design.

## Current state

- The synthetic banking proxy, typed capability schema, discovery loop, deterministic replay, policy gate, sanitized audit trail, and same-session operator handoff are implemented.
- The full suite currently has 27 passing tests.
- The legacy UI has a visible synthetic scenario catalog covering success, recovery, business outcomes, intervention, target failures, blocked requests, and review mismatch. `scripts/verify_demo.py` also generates an explicitly authored unsafe-submission probe that policy must block.
- Existing evidence contains real browser replays driven by the authored example capability.
- `evidence/replay-handoff-simulated/` uses a test actor and must remain labeled as simulated.
- `evidence/replay-handoff-human/` contains sanitized evidence from a completed human-operated same-session recovery.
- `evidence/replay-dialog/` contains a real-browser replay of the genuine discovered artifact proving that an unexpected confirmation is dismissed, redacted, and reported as a distinct hard failure.
- A genuine `gpt-4.1` OpenAI discovery and a keyless replay of its unchanged artifact are recorded under `evidence/`; see `evidence/README.md` for the verified hash and redaction checks.

## Required next work

1. Optionally record a short demo video.
2. Review the final diff, run the complete test suite, and push the finished repository publicly.

## Invariants

- Never commit `.env`, API keys, credentials, raw member values, screenshots containing unmasked data, or the ignored `runs/` directory.
- Never describe an authored artifact as model-discovered or a simulated operator as a human operator.
- Replay must not import or instantiate an OpenAI client.
- Every browser action must pass through both session ownership and policy enforcement.
- `Create account` must remain blocked. The capability stops at the verified review screen.
- A missing member and nickname rejection are business outcomes; permission denial is a failure; loading is bounded recovery; session expiry is an intervention condition.
- Do not add selector fallbacks that click ambiguous controls.
- Persisted results omit outputs; authorized caller output is printed separately.
- Maintain the exact seven headings required in `REPORT.md`.

## Verification

```bash
python -m pip install -e '.[dev]'
python -m playwright install chromium
python -m ruff check bank_automation tests scripts
python -m ruff format --check bank_automation tests scripts
python -m pytest -q
```

When changing discovery or replay, test at least success, not-found, validation rejection, permission denial, slow loading, ambiguous targets, blocked final submission, and same-session handoff.
