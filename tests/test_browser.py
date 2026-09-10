"""Real Chromium integration tests. Handoff uses a simulated operator, explicitly labeled."""

import asyncio
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from bank_automation.audit import Audit
from bank_automation.engine import replay
from bank_automation.models import Capability, Inputs
from bank_automation.operator import Controller
from bank_automation.policy import Policy
from bank_automation.server import Handler
from bank_automation.surface import BrowserSurface

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def app():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


@pytest.mark.parametrize(
    "scenario,member,nickname,status,code",
    [
        ("normal", "23456", "Travel Fund", "success", "review_verified"),
        ("normal", "99999", "Travel Fund", "business_outcome", "member_not_found"),
        ("normal", "12345", "reserved", "business_outcome", "validation_rejected"),
        ("denied", "12345", "Travel Fund", "failure", "permission_denied"),
        ("slow", "34567", "Rainy Day", "success", "review_verified"),
        ("stuck", "12345", "Travel Fund", "failure", "intervention_required"),
        ("expired", "12345", "Travel Fund", "failure", "intervention_required"),
        ("ambiguous", "12345", "Travel Fund", "failure", "action_failed"),
        ("disabled", "12345", "Travel Fund", "failure", "action_failed"),
        ("drift", "12345", "Travel Fund", "failure", "action_failed"),
        ("blocked", "12345", "Travel Fund", "failure", "navigation_blocked"),
        ("dialog", "12345", "Travel Fund", "failure", "unexpected_dialog"),
        (
            "review_mismatch",
            "12345",
            "Travel Fund",
            "failure",
            "success_checkpoint_unmet",
        ),
    ],
)
def test_replay(app, tmp_path, scenario, member, nickname, status, code):
    async def run():
        policy = Policy.load(ROOT / "config/policy.json")
        policy.origin = app
        audit = Audit(tmp_path)
        c = Controller(audit)
        s = BrowserSurface(policy, c, audit)
        try:
            await s.open(app + "/?scenario=" + scenario)
            cap = Capability.model_validate_json(
                (ROOT / "examples/prepare-subaccount.json").read_text()
            )
            result = await replay(s, cap, Inputs(member_id=member, nickname=nickname))
            assert (result.status, result.code) == (status, code)
            if status == "success":
                assert result.outputs["nickname"] == nickname
            assert member not in audit.path.read_text()
            assert nickname not in audit.path.read_text()
            if scenario == "dialog":
                assert "dismissed_unexpected_dialog" in audit.path.read_text()
        finally:
            await s.close()

    asyncio.run(run())


def test_same_session_handoff(app, tmp_path):
    async def run():
        policy = Policy.load(ROOT / "config/policy.json")
        policy.origin = app
        audit = Audit(tmp_path)
        c = Controller(audit)
        s = BrowserSurface(policy, c, audit)
        try:
            await s.open(app + "/?scenario=expired")
            page = s.page
            cap = Capability.model_validate_json(
                (ROOT / "examples/prepare-subaccount.json").read_text()
            )
            task = asyncio.create_task(
                replay(s, cap, Inputs(member_id="12345", nickname="Trip"), handoff=True)
            )
            async with asyncio.timeout(15):
                while c.owner != "PAUSED":
                    await asyncio.sleep(0.02)
                await c.queue.put("claim")
                while c.owner != "HUMAN":
                    await asyncio.sleep(0.02)
                with pytest.raises(PermissionError):
                    await s.act(
                        cap.steps[0], Inputs(member_id="12345", nickname="Trip")
                    )
                await s.frame.get_by_label("Operator name").fill("Test operator")
                await s.frame.get_by_label("Training password").fill(
                    "synthetic-password"
                )
                await s.frame.get_by_role("button", name="Restore session").click()
                await c.queue.put("resume")
                result = await task
            assert result.status == "success"
            assert s.page is page
            text = audit.path.read_text()
            assert "human_action" in text
            assert "synthetic-password" not in text
            assert "Test operator" not in text
        finally:
            await s.close()

    asyncio.run(run())


def test_ambiguous_target_stops_before_click(app, tmp_path):
    async def run():
        policy = Policy.load(ROOT / "config/policy.json")
        policy.origin = app
        audit = Audit(tmp_path)
        c = Controller(audit)
        s = BrowserSurface(policy, c, audit)
        try:
            await s.open(app + "/")
            cap = Capability.model_validate_json(
                (ROOT / "examples/prepare-subaccount.json").read_text()
            )
            await s.frame.locator("button").evaluate("(e)=>e.after(e.cloneNode(true))")
            result = await replay(s, cap, Inputs(member_id="12345", nickname="Trip"))
            assert result.code == "action_failed"
            assert result.step == "step_2"
            assert await s.state() == "Member search"
        finally:
            await s.close()

    asyncio.run(run())


def test_submission_policy_blocks_real_browser(app, tmp_path):
    from bank_automation.models import Step, Target

    async def run():
        policy = Policy.load(ROOT / "config/policy.json")
        policy.origin = app
        audit = Audit(tmp_path)
        c = Controller(audit)
        s = BrowserSurface(policy, c, audit)
        try:
            await s.open(app + "/")
            cap = Capability.model_validate_json(
                (ROOT / "examples/prepare-subaccount.json").read_text()
            )
            inputs = Inputs(member_id="12345", nickname="Trip")
            assert (await replay(s, cap, inputs)).status == "success"
            step = Step(
                id="submit",
                action="click",
                target=Target(strategy="role", role="button", name="Create account"),
                precondition="Review sub-account",
                postcondition="Account created",
            )
            with pytest.raises(PermissionError):
                await s.act(step, inputs)
            assert await s.state() == "Review sub-account"
            assert (
                await s.screenshot()
            )  # Exercise the masked image path used by discovery.
        finally:
            await s.close()

    asyncio.run(run())
