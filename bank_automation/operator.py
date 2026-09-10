"""One run, one local operator, explicit ownership. No remote co-browsing."""

import asyncio
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Controller:
    def __init__(self, audit):
        self.owner = "AUTOMATION"
        self.audit = audit
        self.lock = asyncio.Lock()
        self.request = None
        self.queue = asyncio.Queue()
        self.server = None
        self.token = secrets.token_urlsafe(24)
        self.loop = None

    def start(self):
        self.loop = asyncio.get_running_loop()
        controller = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path != "/" + controller.token:
                    self.send_error(404)
                    return
                body = (
                    "<!doctype html><title>Operator handoff</title><h1>Operator handoff</h1>"
                    "<p>Claim the session, operate the existing browser window, then return control.</p>"
                    "<pre>"
                    + json.dumps(
                        {"owner": controller.owner, "intervention": controller.request},
                        indent=2,
                    )
                    + "</pre>"
                    '<form method="post"><button name="command" value="claim">Take control</button> '
                    '<button name="command" value="resume">Return control</button> '
                    '<button name="command" value="abort">Abort run</button></form>'
                    "<p>Refresh to see the latest state. Field values are not recorded.</p>"
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                if self.path != "/" + controller.token:
                    self.send_error(404)
                    return
                origin = self.headers.get("Origin")
                expected = f"http://127.0.0.1:{controller.server.server_port}"
                if origin and origin != expected:
                    self.send_error(403)
                    return
                length = int(self.headers.get("Content-Length", "0"))
                if length > 100:
                    self.send_error(413)
                    return
                command = self.rfile.read(length).decode().removeprefix("command=")
                if command not in {"claim", "resume", "abort"}:
                    self.send_error(400)
                    return
                controller.loop.call_soon_threadsafe(
                    controller.queue.put_nowait, command
                )
                self.send_response(303)
                self.send_header("Location", "/" + controller.token)
                self.end_headers()

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        print(
            f"Operator: http://127.0.0.1:{self.server.server_port}/{self.token}",
            flush=True,
        )

    def transition(self, owner):
        self.owner = owner
        self.audit.event("control_transfer", owner=owner)

    async def intervene(self, step, state, code, timeout=180):
        self.transition("PAUSED")
        self.request = {
            "capability": "prepare_savings_subaccount",
            "step": step,
            "state": state,
            "code": code,
        }
        self.audit.event("intervention_requested", step=step, state=state, code=code)
        try:
            async with asyncio.timeout(timeout):
                while True:
                    command = await self.queue.get()
                    if command == "abort":
                        return False
                    if command == "claim" and self.owner == "PAUSED":
                        self.transition("HUMAN")
                    elif command == "resume" and self.owner == "HUMAN":
                        self.transition("RESUME_CHECK")
                        return True
        except TimeoutError:
            return False

    def close(self):
        self.transition("FINISHED")
        if self.server:
            self.server.shutdown()
            self.server.server_close()
