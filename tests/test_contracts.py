import asyncio
from pathlib import Path

import pytest
from pydantic import ValidationError

from bank_automation.audit import Audit
from bank_automation.models import Capability, Inputs, Step, Target
from bank_automation.operator import Controller
from bank_automation.policy import SCENARIOS, Policy

ROOT = Path(__file__).resolve().parents[1]


def test_artifact_contract():
    cap = Capability.model_validate_json(
        (ROOT / "examples/prepare-subaccount.json").read_text()
    )
    assert cap.provenance == "authored_example"
    assert cap.steps[0].input_ref == "member_id"
    bad = cap.model_dump()
    bad["steps"][0]["literal"] = "12345"
    with pytest.raises(ValidationError):
        Capability.model_validate(bad)
    bad = cap.model_dump()
    bad["outputs"]["nickname"]["sensitive"] = False
    with pytest.raises(ValidationError):
        Capability.model_validate(bad)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/",
        "http://127.0.0.1:8765.evil.test/",
        "http://127.0.0.1:8765/admin",
        "http://127.0.0.1:8765/?token=secret",
        "http://127.0.0.1:8765/?scenario=unknown",
    ],
)
def test_url_denied(url):
    assert not Policy.load(ROOT / "config/policy.json").allows_url(url)


def test_supported_scenario_urls_allowed():
    policy = Policy.load(ROOT / "config/policy.json")
    assert policy.allows_url("http://127.0.0.1:8765/")
    for scenario in SCENARIOS:
        assert policy.allows_url(f"http://127.0.0.1:8765/?scenario={scenario}"), (
            scenario
        )


def test_final_submission_blocked():
    step = Step(
        id="submit",
        action="click",
        target=Target(strategy="role", role="button", name="Create account"),
        precondition="Review sub-account",
        postcondition="Account created",
    )
    with pytest.raises(PermissionError):
        Policy.load(ROOT / "config/policy.json").check(
            step, "Review sub-account", "http://127.0.0.1:8765/"
        )


def test_raw_data_not_logged(tmp_path):
    audit = Audit(tmp_path)
    audit.event(
        "action",
        password="super-secret",
        member_id="12345",
        raw_dom="<secret>",
        code="safe_code",
    )
    assert "super-secret" not in audit.path.read_text()
    assert "12345" not in audit.path.read_text()


def test_input_validation():
    for args in [
        {"member_id": "abc", "nickname": "Trip"},
        {"member_id": "12345", "nickname": " "},
        {"member_id": "12345", "nickname": "x" * 31},
    ]:
        with pytest.raises(ValidationError):
            Inputs(**args)


def test_ownership_protocol(tmp_path):
    async def run():
        c = Controller(Audit(tmp_path))
        task = asyncio.create_task(
            c.intervene("step_4", "Session expired", "expired", timeout=1)
        )
        await asyncio.sleep(0)
        assert c.owner == "PAUSED"
        await c.queue.put("resume")
        await asyncio.sleep(0)
        assert c.owner == "PAUSED"
        await c.queue.put("claim")
        await asyncio.sleep(0)
        assert c.owner == "HUMAN"
        await c.queue.put("resume")
        assert await task
        assert c.owner == "RESUME_CHECK"

    asyncio.run(run())
