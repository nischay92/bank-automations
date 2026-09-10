# 1. Architecture

The project is one Python package plus a local synthetic banking UI. The UI uses tables, normal labels, and an iframe without test IDs. Its workflow is member search → member details → savings account → sub-account form → review. The final creation control exists but is outside automation policy. Application data lives only in the local browser; no servicing API is exposed or invoked.

Discovery receives a goal, a masked screenshot, a sanitized visible-control inventory, and action-history metadata. OpenAI chooses one structured action at a time. A temporary reference resolves to a scoped label or role locator; policy is checked at execution, and the observed transition is recorded. Parameter references are explicit from the first fill action. Model completion is only a proposal: a separate checkpoint verifies member ID, account type, and nickname on the review screen. The action sequence is not encoded in the discovery prompt. Application vocabulary, known outcomes, and final verification are authored adapters, not supposedly learned exception handling.

Replay, discovery, browser interaction, policy, audit, and control ownership have separate modules. They run in one process; queues, distributed workers, and service orchestration would obscure the core. Replay never constructs a model client. The included example is authored, and must not be confused with the still-required genuine discovery artifact.

# 2. Artifact schema

Pydantic models forbid unknown fields and emit JSON Schema. The artifact carries separate schema and capability versions, application/UI identity, provenance, typed input/output contracts, effect scope, ordered steps, outcome-rule version, and a final success predicate. Inputs constrain member IDs and nicknames. A fill stores `input_ref`, not its discovery value. Output descriptors declare source, type, and sensitivity; sensitive output values are returned to the caller but omitted from saved results.

Steps contain an ID, action enum, frame-scoped target, input binding or constrained literal, precondition, postcondition, and timeout. Screen checkpoints are supplemented by field-value verification for same-screen edits. Only supported contract shapes are accepted in version 1; this deliberately avoids an arbitrary expression or code execution language. No executable scripts or model transcripts are stored in capabilities.

Reviewers can inspect the exact action sequence and required effect. The included genuine OpenAI discovery artifact was replayed unchanged at SHA-256 `e10ab9321fe66e3129f027024a5213716832b62a773f2b93d769366f454ab2c4`. Provenance labels document origin but are not cryptographic attestations. A production registry would hash/sign reviewed artifacts and bind approval to the hash and policy version. Policy remains independent: importing an artifact cannot grant permissions.

# 3. Determinism & error handling

Replay resolves exact accessible labels or role/name targets within the named iframe. It requires one visible, enabled match; missing or ambiguous controls stop execution. There is no broad selector fallback or coordinate guessing. The locator is resolved again immediately before the action. Each screen transition has a bounded wait; the known Loading state is observed and logged without retrying clicks. Same-screen input edits verify their actual values, and the terminal checkpoint verifies the requested review contents.

Results distinguish success with outputs, expected business outcomes (missing member, rejected nickname), and failures (permission denial, policy violation, unresolved intervention, action/checkpoint failure). Application rules are explicitly versioned as northstar-v1. Session expiry or an unknown state produces sanitized context and optionally a live handoff. Failure snapshots contain only approved screen/control descriptions, never arbitrary page text. Persisted logs contain action metadata, checkpoints, ownership changes, model response IDs, and reason codes.

No mutation is automatically retried. Following human intervention, replay verifies the expected postcondition; if it cannot establish the checkpoint, it stops. This is conservative and prevents duplicate actions. Runtime validation of compatible UI behavior currently comes from checkpoints and targeting; the declared UI version is not a vendor fingerprint. The synthetic application exposes named scenarios for duplicate, disabled, and renamed controls, blocked requests, stuck loading, and review mismatches so these fail-closed behaviors can be demonstrated without test-only DOM mutation. The submitted evidence includes a genuine `gpt-4.1` discovery and a replay of its unchanged artifact with different synthetic inputs and the OpenAI key unset.

# 4. Heterogeneity & multi-tenant

The BrowserSurface boundary contains perception, target resolution, actuation, and verification. A small Surface protocol formalizes observation, action, settling, and verification methods for both engines. Browser-specific locators remain inside target descriptors. A desktop adapter would need distinct accessibility selectors (window identity, automation ID, role/name) and window/process allowlists. A visual-only adapter would need tested anchor matching and confidence/ambiguity rules. Raw coordinate replay is not implemented or claimed reliable.

The current adapter supports labels, roles, and explicit frames. Label-relative table locators for less semantic legacy pages are a planned strategy, not an implemented fallback. The proxy deliberately retains enough ordinary accessibility information to make this slice reliable.

At scale, store a reviewed vendor/product capability separately from tenant bindings: allowed origin, entry point, credentials reference, frame/label overrides, and compatible version range. Typed overrides may specialize target descriptions but must not expand effects or alter business semantics without review. Bind replay to an approved base+override hash. Run canary replays against each supported vendor/version variant; quarantine mismatched checkpoints instead of silently rewriting artifacts. Credentials remain in a tenant secret store and outputs in an authorized tenant-specific result channel. Multi-tenant isolation is design-only here.

# 5. Escalation & handoff

Ownership transitions through AUTOMATION, PAUSED, HUMAN, RESUME_CHECK, and FINISHED. All automated actions check ownership under an asyncio lock; only one action executes at a time. A local operator page routes requests containing capability, stopped step, safe state, and reason. A tokenized URL and Origin check protect this local demonstration from basic accidental/foreign-page mutations; this is not full identity or authorization infrastructure.

An operator claims the paused session, works in the same headed browser, and returns control. Event listeners record approved control names and event types, never typed values. The runner validates the resume checkpoint before resuming. A person may physically interact with a headed browser outside the protocol; this demo does not provide OS-level access isolation. Login repair is real in-session UI interaction using synthetic credentials. Evidence includes one completed human-operated handoff and, separately labeled, a headless integration run that uses a simulated operator.

Discovery that requires manual workflow changes does not silently publish an incomplete capability: it stops and requires rerecording. Unexpected dialogs are dismissed without persisting their text and reported as a distinct hard failure; ambiguous targets stop without a click. A production console would add authenticated operator identity, leases, a live remote browser viewport, stronger action capture, and session isolation.

# 6. Safety

The independently configured allowlist constrains origin, routes, request method, and state/action/control combinations. All requests are intercepted, service workers are disabled, and both engines share the action gate. Only preparation actions are allowed; final account creation and automated login are blocked. Exact input-to-control bindings prevent a model from typing a nickname into the member-ID field. Unknown effects default to deny.

Artifacts and logs contain approved UI vocabulary and parameter references. Screenshots for discovery are masked in memory and never saved. Model prompts exclude parameter values; the application receives them only during execution. Goal text is supplied by the caller and sent to the provider, so it must contain no secrets. The screenshot masking strategy is specific to this synthetic app, not a generic PII detector. Provider-side processing still occurs; `store=False` does not guarantee zero retention. Real banking deployment needs approved provider retention controls, comprehensive observation redaction, authenticated invocation, secure input transport, and tenant isolation.

The CLI returns outputs on stdout as its caller interface. Redirecting those outputs or supplying real inputs on a shared command line could leak data; this demo is synthetic-only. Production should use an authenticated invocation channel and secret references. Policy relies on the reviewed app's control semantics and cannot prove that a compromised page gives a safe button a safe effect.

# 7. Cuts

One workflow, one browser adapter, one local operator, and an ordered step list keep the implementation focused. No production banking backend, real authentication, account mutation, artifact approval registry, desktop implementation, generic visual targeting, or multi-tenant infrastructure is included. Unsupported versions and layouts stop rather than attempt model repair during replay.

Next priorities: demonstrate manual handoff, add artifact approval/hash binding, strengthen observation types, implement and test a label-relative legacy locator, and validate a second tenant variant. Broader workflows and scaling infrastructure come after those boundaries are proven.
