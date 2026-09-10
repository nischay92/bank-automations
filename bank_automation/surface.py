import asyncio
import base64
import os
import time

from playwright.async_api import async_playwright

from .models import Target

SCREENS = {
    "Member search",
    "Member details",
    "Savings account",
    "New sub-account",
    "Review sub-account",
    "Member not found",
    "Validation rejected",
    "Permission denied",
    "Session expired",
    "Loading",
    "Account created",
}
CONTROL_NAMES = {
    "Member ID",
    "Search",
    "View savings",
    "New sub-account",
    "Account type",
    "Nickname",
    "Review",
    "Create account",
    "Operator name",
    "Training password",
    "Restore session",
}


class BrowserSurface:
    def __init__(self, policy, controller, audit):
        self.policy, self.controller, self.audit = policy, controller, audit
        self.refs = {}
        self.blocked = False

    async def open(self, url, headed=False):
        if not self.policy.allows_url(url):
            raise PermissionError("target_not_allowed")
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(
            headless=not headed, executable_path=os.getenv("BROWSER_EXECUTABLE") or None
        )
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 900}, service_workers="block"
        )

        async def route(r):
            if self.policy.allows_url(r.request.url) and r.request.method == "GET":
                await r.continue_()
            else:
                self.blocked = True
                await r.abort()

        await self.context.route("**/*", route)
        await self.context.expose_binding("auditHuman", self.human_event)
        await self.context.add_init_script("""
          for (const type of ['click','change']) document.addEventListener(type,e=>{
            const el=e.target;
            const name=el.labels?.[0]?.textContent?.trim() || el.textContent?.trim() || '';
            window.auditHuman({type,name}).catch(()=>{});
          },true);
        """)
        self.page = await self.context.new_page()
        self.dialog = False

        async def dismiss_unexpected_dialog(dialog):
            self.dialog = True
            self.audit.event("unexpected_dialog", code="dismissed_unexpected_dialog")
            await dialog.dismiss()

        self.page.on("dialog", dismiss_unexpected_dialog)
        await self.page.goto(url)
        await self.frame.get_by_role(
            "heading", name="Member search", exact=True
        ).wait_for()

    async def human_event(self, source, event):
        if self.controller.owner == "HUMAN":
            name = event.get("name")
            self.audit.event(
                "human_action",
                action=event.get("type")
                if event.get("type") in {"click", "change"}
                else "unknown",
                control=name if name in CONTROL_NAMES else "unrecognized_control",
            )

    @property
    def frame(self):
        return self.page.frame_locator('iframe[title="Member workspace"]')

    def locator(self, target):
        if target.strategy == "label":
            return self.frame.get_by_label(target.name, exact=True)
        return self.frame.get_by_role(target.role, name=target.name, exact=True)

    async def state(self):
        if self.blocked:
            return "Blocked navigation"
        if self.dialog:
            return "Unexpected dialog"
        try:
            headings = await self.frame.get_by_role(
                "heading", level=1
            ).all_text_contents()
            return (
                headings[0]
                if len(headings) == 1 and headings[0] in SCREENS
                else "Unknown screen"
            )
        except Exception:
            return "Unknown screen"

    async def observe(self):
        state = await self.state()
        controls = []
        self.refs = {}
        for node in await self.frame.locator("input,select,button").all():
            if not await node.is_visible():
                continue
            desc = await node.evaluate("""e=>({tag:e.tagName.toLowerCase(),
                name:e.labels?.[0]?.textContent.trim()||e.textContent.trim(),type:e.type})""")
            if desc["name"] not in CONTROL_NAMES:
                continue
            role = (
                "button"
                if desc["tag"] == "button"
                else ("combobox" if desc["tag"] == "select" else "textbox")
            )
            target = Target(
                strategy="role" if role == "button" else "label",
                role=role,
                name=desc["name"],
            )
            ref = f"c{len(controls) + 1}"
            self.refs[ref] = target
            controls.append({"ref": ref, "role": role, "name": desc["name"]})
        return {"screen": state, "controls": controls}

    async def screenshot(self):
        # In-memory only. Mask all input values and member/account detail containers.
        data = await self.page.screenshot(
            mask=[
                self.frame.locator("input"),
                self.frame.locator("dl"),
                self.frame.locator("p:not(.muted):not(.notice)"),
            ]
        )
        return base64.b64encode(data).decode()

    async def act(self, step, inputs):
        async with self.controller.lock:
            if self.controller.owner != "AUTOMATION":
                raise PermissionError("automation_does_not_own_session")
            state = await self.state()
            if state != step.precondition:
                raise RuntimeError("precondition_mismatch")
            self.policy.check(step, state, self.page.url)
            loc = self.locator(step.target)
            if await loc.count() != 1:
                raise RuntimeError("target_ambiguous_or_missing")
            if not await loc.is_visible() or not await loc.is_enabled():
                raise RuntimeError("target_not_actionable")
            if step.action == "click":
                await loc.click(timeout=step.timeout_ms)
            elif step.action == "fill":
                await loc.fill(getattr(inputs, step.input_ref), timeout=step.timeout_ms)
            else:
                await loc.select_option(step.literal, timeout=step.timeout_ms)
            self.audit.event(
                "action_executed",
                step=step.id,
                action=step.action,
                state=state,
                control=step.target.name,
            )

    async def settle(self, before, expect_change, timeout_ms=5000):
        deadline = time.monotonic() + timeout_ms / 1000
        loading = False
        while time.monotonic() < deadline:
            state = await self.state()
            if state == "Loading":
                if not loading:
                    self.audit.event(
                        "recovery_wait", state=state, code="bounded_load_wait"
                    )
                    loading = True
            elif state != "Unknown screen" and (not expect_change or state != before):
                return state
            await asyncio.sleep(0.05)
        return await self.state()

    async def verify_field(self, step, inputs):
        expected = getattr(inputs, step.input_ref) if step.input_ref else step.literal
        return await self.locator(step.target).input_value() == expected

    async def verify(self, inputs):
        if await self.state() != "Review sub-account":
            return None

        async def field(name):
            loc = (
                self.frame.locator("dt")
                .filter(has_text=__import__("re").compile("^" + name + "$"))
                .locator("xpath=following-sibling::dd[1]")
            )
            if await loc.count() != 1:
                return None
            return await loc.inner_text()

        if (
            await field("Member ID") != inputs.member_id
            or await field("Nickname") != inputs.nickname
            or await field("Account type") != "Savings"
        ):
            return None
        return {
            "account_type": "savings",
            "nickname": inputs.nickname,
            "review_verified": True,
        }

    async def close(self):
        if hasattr(self, "browser"):
            await self.browser.close()
        if hasattr(self, "pw"):
            await self.pw.stop()
