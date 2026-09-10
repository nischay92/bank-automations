"""Generate real browser replay evidence, without a model. Run from repo root."""

import argparse
import asyncio
import json
import shutil
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from bank_automation.cli import execute
from bank_automation.models import Capability, Step, Target
from bank_automation.server import Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="runs/verification")
    parser.add_argument("--artifact", default="examples/prepare-subaccount.json")
    args = parser.parse_args()
    output = Path(args.output)
    artifact = Path(args.artifact)
    Capability.model_validate_json(artifact.read_text())
    output.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    cases = [
        ("success", "normal", "23456", "Travel Fund", 0),
        ("not-found", "normal", "99999", "Travel Fund", 0),
        ("slow", "slow", "34567", "Rainy Day", 0),
        ("stuck", "stuck", "12345", "Travel Fund", 1),
        ("denied", "denied", "12345", "Travel Fund", 1),
        ("validation", "normal", "12345", "reserved", 0),
        ("expiry", "expired", "12345", "Travel Fund", 1),
        ("ambiguous", "ambiguous", "12345", "Travel Fund", 1),
        ("disabled", "disabled", "12345", "Travel Fund", 1),
        ("drift", "drift", "12345", "Travel Fund", 1),
        ("blocked", "blocked", "12345", "Travel Fund", 1),
        ("dialog", "dialog", "12345", "Travel Fund", 1),
        ("review-mismatch", "review_mismatch", "12345", "Travel Fund", 1),
    ]
    try:
        for name, scenario, member, nickname, expected_exit in cases:
            ns = argparse.Namespace(
                command="replay",
                policy="config/policy.json",
                artifact=str(artifact),
                inputs=json.dumps({"member_id": member, "nickname": nickname}),
                run_dir=str(output / f"replay-{name}"),
                target=f"http://127.0.0.1:8765/?scenario={scenario}",
                headed=False,
                handoff=False,
            )
            assert asyncio.run(execute(ns)) == expected_exit, name

        # Deliberately authored adversarial probe: artifact contents cannot expand policy.
        authored_capability = Capability.model_validate_json(
            Path("examples/prepare-subaccount.json").read_text()
        )
        unsafe = authored_capability.model_dump()
        unsafe["steps"].append(
            Step(
                id="step_7_unsafe_submission",
                action="click",
                target=Target(strategy="role", role="button", name="Create account"),
                precondition="Review sub-account",
                postcondition="Account created",
            ).model_dump()
        )
        unsafe_capability = Capability.model_validate(unsafe)
        unsafe_artifact = output / "authored-unsafe-submission-probe.json"
        unsafe_artifact.write_text(unsafe_capability.model_dump_json(indent=2))
        unsafe_args = argparse.Namespace(
            command="replay",
            policy="config/policy.json",
            artifact=str(unsafe_artifact),
            inputs=json.dumps({"member_id": "12345", "nickname": "Travel Fund"}),
            run_dir=str(output / "replay-policy-block"),
            target="http://127.0.0.1:8765/?scenario=normal",
            headed=False,
            handoff=False,
        )
        assert asyncio.run(execute(unsafe_args)) == 1
        shutil.copyfile(artifact, output / "input-capability.json")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
