# Evidence status

This directory contains real deterministic Playwright executions against the local synthetic banking UI.

| Path | Provenance | Result |
| --- | --- | --- |
| `authored-capability.json` | Authored example, not LLM discovery | Replay input for current evidence |
| `discovered-capability.json` | Genuine OpenAI discovery with `gpt-4.1` | Live-discovered, typed capability |
| `discovery-live/` | Genuine OpenAI discovery against the synthetic UI | Success; review independently verified |
| `replay-live-artifact/` | Model-free replay of the unchanged discovered artifact | Success with different synthetic inputs and OpenAI environment unset |
| `replay-success/` | Real browser replay | Success with a different member ID |
| `replay-slow/` | Real browser replay | Bounded loading recovery, then success |
| `replay-not-found/` | Real browser replay | Known business outcome |
| `replay-validation/` | Real browser replay | Known validation outcome |
| `replay-denied/` | Real browser replay | Hard permission failure |
| `replay-dialog/` | Real browser replay of the genuine discovered artifact | Unexpected confirmation dismissed; distinct hard failure |
| `replay-expiry/` | Real browser replay | Intervention required |
| `replay-handoff-simulated/` | Real browser/session; test actor performs operator actions | Same-session pause, claim, resume, success |
| `replay-handoff-human/` | Real browser/session; human operator performed the recovery | Same-session pause, claim, manual recovery, resume, success |

Each run contains `events.jsonl` and a persisted result that explicitly omits outputs. Failure paths also contain a sanitized structural snapshot. The slow run logs `recovery_wait`. The handoff run logs PAUSED, HUMAN, RESUME_CHECK, and AUTOMATION transitions plus control-level human actions without values.

The dialog run uses the genuine discovered artifact, dismisses the unexpected modal to prevent a blocked browser session, and reports `failure: unexpected_dialog`. Neither the dialog message nor entered values are persisted.

`replay-handoff-human/` was produced by a person following the local operator URL and restoring the synthetic expired session in the existing headed browser. Its logs record control names and ownership changes but omit the operator name, training password, member ID, nickname, and page values. `replay-handoff-simulated/` remains separately and accurately labeled as test-actor evidence.

## Genuine discovery verification

The live artifact and evidence were created with the README workflow and checked as follows:

1. The capability says `"provenance": "live_llm_discovery"`, records `gpt-4.1`, and validates against the strict capability model.
2. `discovery-live/events.jsonl` includes `discovery_started`, seven `model_decision` events with response IDs, six recorded transitions, and `artifact_recorded`.
3. The artifact SHA-256 was `e10ab9321fe66e3129f027024a5213716832b62a773f2b93d769366f454ab2c4` before and after replay.
4. `replay-live-artifact/` was run with different synthetic inputs and both `OPENAI_API_KEY` and `OPENAI_MODEL` unset; it contains no model events.
5. Automated byte scans found no discovery/replay input values, API key, authorization header, screenshots/data URLs, or raw model-output field in the new artifact and run evidence. Persisted results omit outputs.
6. A short manual screen recording, if added, must clearly label synthetic data and show the same-session operator handoff.

Do not rename the authored artifact or these tests to imply they are LLM-generated or human-operated evidence.
