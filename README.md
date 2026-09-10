# Bank capabilities

A focused computer-use assessment: a model discovers a UI workflow; a typed artifact records it; deterministic replay prepares a savings sub-account without a model. Python, Playwright, Pydantic, and a local synthetic banking UI.

**Submission status:** implementation, authored example, genuine OpenAI discovery evidence, and keyless replay evidence are included. The authored example remains explicitly labeled and is not presented as model-generated. No API key is included. See `evidence/README.md` for verification status.

## Reviewer quick tour: no setup required

The repository contains the complete end-to-end proof. These files show the system without requiring an API key or local execution:

| What to inspect | Stored proof | What it demonstrates |
| --- | --- | --- |
| Genuine discovery artifact | [`evidence/discovered-capability.json`](evidence/discovered-capability.json) | Typed, versioned capability created by a real `gpt-4.1` UI-discovery run |
| Discovery run | [`evidence/discovery-live/events.jsonl`](evidence/discovery-live/events.jsonl), [`result.json`](evidence/discovery-live/result.json) | Seven model decisions with response IDs, six executed transitions, independent success verification |
| Model-free replay | [`evidence/replay-live-artifact/events.jsonl`](evidence/replay-live-artifact/events.jsonl), [`result.json`](evidence/replay-live-artifact/result.json) | The unchanged discovered artifact replayed with different inputs and OpenAI variables unset |
| Runtime failure | [`evidence/replay-dialog/events.jsonl`](evidence/replay-dialog/events.jsonl), [`snapshot`](evidence/replay-dialog/failure.snapshot.json) | Unexpected confirmation dismissed and reported as `failure: unexpected_dialog` without persisting its text |
| Human handoff | [`evidence/replay-handoff-human/events.jsonl`](evidence/replay-handoff-human/events.jsonl), [`result.json`](evidence/replay-handoff-human/result.json) | Real person takes control of the same browser, restores the session, returns control, and replay succeeds |
| Broader outcomes | [`evidence/README.md`](evidence/README.md) | Success, slow recovery, not-found, validation, permission, expiry, dialog, and simulated handoff evidence |
| Design decisions | [`REPORT.md`](REPORT.md) | Architecture, artifact schema, determinism, scale, handoff, safety, and deliberate cuts |

The live artifact SHA-256 is `e10ab9321fe66e3129f027024a5213716832b62a773f2b93d769366f454ab2c4`; it was unchanged before and after keyless replay.

## What is implemented

- **LLM discovery:** an observe → decide → act loop drives a real rendered UI using screenshots and a sanitized control inventory.
- **Reusable capability:** strict Pydantic contracts record parameter references, stable targets, pre/postconditions, outputs, versions, provenance, and effect scope—not a model transcript.
- **Deterministic replay:** the saved artifact runs without importing or constructing an OpenAI client and verifies every checkpoint and output.
- **Explicit runtime outcomes:** business outcomes, recoverable waits, intervention conditions, and hard failures have separate structured results.
- **Live-session human handoff:** automation pauses, transfers ownership, records safe human action metadata, checks the repaired state, and resumes the same browser.
- **Independent safety:** origin/route/action allowlists, exact parameter bindings, ambiguous-target rejection, masked observations, sanitized evidence, and a blocked final `Create account` action.

## Assignment coverage

| PDF requirement | Implementation and proof |
| --- | --- |
| Goal-driven agent loop | `engine.discover` accepts goal + target, operates the live UI, and has bounded steps, API timeouts, and an overall deadline |
| Structured capability artifact | Strict schema in `models.py`; authored schema/example under `examples/`; genuine artifact under `evidence/` |
| Deterministic replay | `engine.replay` performs stable frame-scoped label/role targeting with no model client and verifies fields, screens, and outputs |
| Error and exception handling | Structured business, recovery, intervention, and failure outcomes; real replay evidence includes snapshots |
| Safety and data handling | Independent `config/policy.json`, unknown-effect denial, masked screenshots, allowlisted audit fields, omitted persisted outputs |
| Evidence and observability | Discovery decisions/response IDs, replay actions/checkpoints, failure snapshots, redaction checks, and artifact hash |
| Human escalation and handoff | Real ownership state machine plus both automated integration proof and a completed human-operated same-session recovery |
| Heterogeneity and scale design | `Surface` seam and the tenant/version strategy are documented under the required headings in `REPORT.md` |

## Setup

Python 3.11+ is required. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m playwright install chromium
```

On Windows, activate with `.venv\Scripts\activate`. On Linux, browser system dependencies may require `python -m playwright install --with-deps chromium`. For an existing compatible Chromium installation, set `BROWSER_EXECUTABLE` to its executable path.

Start the UI in terminal one:

```bash
bank-demo
```

Open http://127.0.0.1:8765 in a browser to inspect it. The left navigation provides a reviewer-friendly scenario catalog. Synthetic member IDs: `12345`, `23456`, `34567`. No real credentials or financial data. The automation uses only the rendered UI, never the application's JavaScript variables or internal data.

## Quick demo without a model or API key

Terminal two, from the repository root with the virtual environment activated:

```bash
env -u OPENAI_API_KEY -u OPENAI_MODEL automation replay \
  --artifact evidence/discovered-capability.json \
  --inputs '{"member_id":"23456","nickname":"Travel Fund"}' \
  --run-dir runs/reviewer-replay-01 --headed
```

This replays the genuine discovered artifact, checks the review values, and returns typed JSON while the OpenAI variables are explicitly absent. Each run needs a fresh `--run-dir`; increment the suffix when repeating it. Browser state resets per run. Exit status is zero for success or known business outcomes and one for failures. The separately labeled authored example is available at `examples/prepare-subaccount.json`.

## Reproduce genuine discovery, then replay

Copy the ignored environment template, add an API key locally, and load it into the discovery process. Never commit `.env`:

```bash
cp .env.example .env
# Edit .env locally and set OPENAI_API_KEY. Do not paste the key into source files.
set -a
source .env
set +a

automation discover \
  --goal 'Find the member identified by member_id. Prepare a new savings sub-account using nickname. Stop at review.' \
  --inputs '{"member_id":"12345","nickname":"Travel Fund"}' \
  --artifact runs/reviewer-discovered.json \
  --run-dir runs/reviewer-discovery-01 --headed

unset OPENAI_API_KEY OPENAI_MODEL

automation replay --artifact runs/reviewer-discovered.json \
  --inputs '{"member_id":"23456","nickname":"Rainy Day"}' \
  --run-dir runs/reviewer-discovered-replay-01 --headed
```

The model is configurable; use a model your account supports that accepts image inputs and strict structured outputs. Discovery calls OpenAI's Responses API with `store=False`, a maximum of 20 decisions by default, a 240-second discovery deadline, and bounded API timeouts. Only discovery imports/constructs an OpenAI client. Goal text goes to OpenAI: use parameter references and synthetic data, never secrets. `store=False` is not a claim of zero provider retention.

Artifacts contain parameter references and allowlisted UI vocabulary. Logs store decision reason codes and response IDs, not raw model responses, screenshots, input values, or API errors. Results on stdout include requested outputs; don't redirect stdout into public evidence for real data.

## Runtime outcomes

Use the same replay command with these changes:

| Scenario | Target / input change | Result |
| --- | --- | --- |
| Missing member | `member_id` = `99999` | `business_outcome: member_not_found` |
| Invalid nickname | `nickname` = `reserved` | `business_outcome: validation_rejected` |
| Permission denied | `--target 'http://127.0.0.1:8765/?scenario=denied'` | `failure: permission_denied` |
| Slow loading | `--target 'http://127.0.0.1:8765/?scenario=slow'` | bounded wait then success |
| Stuck loading | `--target 'http://127.0.0.1:8765/?scenario=stuck'` | `failure: intervention_required` after bounded wait |
| Session expiry | `--target 'http://127.0.0.1:8765/?scenario=expired'` | intervention required |
| Duplicate Search controls | `--target 'http://127.0.0.1:8765/?scenario=ambiguous'` | `failure: action_failed`; no ambiguous click |
| Disabled Search control | `--target 'http://127.0.0.1:8765/?scenario=disabled'` | `failure: action_failed`; no click |
| Renamed Search control | `--target 'http://127.0.0.1:8765/?scenario=drift'` | `failure: action_failed`; no selector fallback |
| Blocked request | `--target 'http://127.0.0.1:8765/?scenario=blocked'` | `failure: navigation_blocked` |
| Unexpected confirmation | `--target 'http://127.0.0.1:8765/?scenario=dialog'` | dialog dismissed, then `failure: unexpected_dialog` |
| Review data mismatch | `--target 'http://127.0.0.1:8765/?scenario=review_mismatch'` | `failure: success_checkpoint_unmet` |
| Unsafe final submission | Full-matrix generator below | `failure: policy_blocked`; account remains uncreated |

Use `examples/prepare-subaccount.json` to replay every scenario. A successful live discovery writes a reusable capability artifact. Failed or incomplete discovery does **not** publish an artifact; it produces a sanitized run result instead, which prevents a partial path from being mislabeled as a discovered capability. To generate a disposable full matrix under the ignored `runs/` directory:

```bash
python scripts/verify_demo.py --output runs/scenario-showcase
```

The generator also creates `authored-unsafe-submission-probe.json` inside its ignored output directory. That file is deliberately authored—not model-discovered—and appends a `Create account` click to demonstrate that replay policy rejects an unsafe artifact regardless of what the artifact requests.

Run the identical matrix with the genuine discovery artifact by changing both the input artifact and the fresh output directory:

```bash
python scripts/verify_demo.py \
  --artifact evidence/discovered-capability.json \
  --output runs/discovered-scenario-showcase
```

## Real human handoff

```bash
automation replay --artifact examples/prepare-subaccount.json \
  --inputs '{"member_id":"12345","nickname":"Travel Fund"}' \
  --target 'http://127.0.0.1:8765/?scenario=expired' \
  --run-dir runs/manual-handoff --headed --handoff
```

1. Open the unique local **Operator** URL printed by the process.
2. When the run pauses, refresh the operator page and click **Take control**.
3. In the automation's existing Chromium window, fill any nonempty synthetic operator name and training password. Click **Restore session**.
4. Return to the operator page and click **Return control**.
5. The runner verifies the new-sub-account screen before continuing. It never reopens the browser or replays the interrupted click.

Intervention expires after 180 seconds or can be aborted. An unsuccessful resume ends the run with a structured failure. The operator page is local, bearer-URL protected, and validates browser Origin on mutation. It is not a remotely deployable authenticated console.

Sanitized evidence from a successfully completed human-operated handoff is included in `evidence/replay-handoff-human/`. The separate `evidence/replay-handoff-simulated/` run remains labeled as test-actor evidence.

## Tests

```bash
python -m ruff check bank_automation tests scripts
python -m ruff format --check bank_automation tests scripts
python -m pytest -q
```

Browser tests start their own local server. They cover different replay parameters, business outcomes, permission denial, recoverable and stuck loading, session expiry, duplicate/disabled/drifted controls, blocked requests, safely dismissed unexpected dialogs, mismatched review data, blocked submission, and a simulated operator in the same live browser. This simulated operator test proves the mechanism; it is not evidence that a person performed a handoff.

## Layout

- `bank_automation/web/`: legacy-style framed proxy with synthetic data.
- `models.py`: strict artifact, input, step, decision, and result contracts.
- `surface.py`: browser perception, targeting, action execution, and output checks.
- `policy.py`, `config/policy.json`: independently configured network and effect allowlists.
- `engine.py`: discovery recorder and model-free replay.
- `operator.py`: local intervention routing and ownership protocol.
- `audit.py`: allowlisted metadata logging and sanitized structural failure snapshots.
- `examples/`: authored reusable capability and generated JSON Schema.
- `REPORT.md`: design decisions, scope, and limitations.
