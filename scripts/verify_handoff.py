"""Create labeled evidence for a simulated operator using the real live-session seam."""

import asyncio
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from bank_automation.audit import Audit
from bank_automation.engine import replay
from bank_automation.models import Capability, Inputs
from bank_automation.operator import Controller
from bank_automation.policy import Policy
from bank_automation.server import Handler
from bank_automation.surface import BrowserSurface

ROOT = Path(__file__).resolve().parents[1]


async def exercise() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    directory = ROOT / "evidence" / "replay-handoff-simulated"
    audit = Audit(directory)
    controller = Controller(audit)
    policy = Policy.load(ROOT / "config/policy.json")
    surface = BrowserSurface(policy, controller, audit)
    result = None
    try:
        await surface.open("http://127.0.0.1:8765/?scenario=expired")
        browser_page = surface.page
        capability = Capability.model_validate_json(
            (ROOT / "examples/prepare-subaccount.json").read_text()
        )
        inputs = Inputs(member_id="12345", nickname="Travel Fund")
        task = asyncio.create_task(replay(surface, capability, inputs, handoff=True))
        async with asyncio.timeout(15):
            while controller.owner != "PAUSED":
                await asyncio.sleep(0.02)
            await controller.queue.put("claim")
            while controller.owner != "HUMAN":
                await asyncio.sleep(0.02)
            await surface.frame.get_by_label("Operator name").fill("Test operator")
            await surface.frame.get_by_label("Training password").fill(
                "synthetic-password"
            )
            await surface.frame.get_by_role("button", name="Restore session").click()
            await controller.queue.put("resume")
            result = await task
        assert result.status == "success"
        assert surface.page is browser_page
        audit.event("verification_note", source="simulated_operator_same_session")
        audit.result(result)
    finally:
        await surface.close()
        controller.close()
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    asyncio.run(exercise())
