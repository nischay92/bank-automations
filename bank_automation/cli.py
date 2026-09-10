import argparse
import asyncio
import os
from pathlib import Path

from .audit import Audit
from .engine import discover, replay
from .models import Capability, Inputs, Result
from .operator import Controller
from .policy import Policy
from .surface import BrowserSurface


async def execute(args):
    inputs = Inputs.model_validate_json(args.inputs)
    policy = Policy.load(args.policy)
    if args.command == "discover" and not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "Set OPENAI_API_KEY locally. No discovery evidence has been generated."
        )
    capability = (
        Capability.model_validate_json(Path(args.artifact).read_text())
        if args.command == "replay"
        else None
    )
    audit = Audit(args.run_dir)
    controller = Controller(audit)
    surface = BrowserSurface(policy, controller, audit)
    result = None
    try:
        if args.handoff:
            controller.start()
        await surface.open(args.target, args.headed)
        audit.event(
            "run_started", source="deterministic_replay" if capability else "discovery"
        )
        result = (
            await replay(surface, capability, inputs, args.handoff)
            if capability
            else await discover(
                surface,
                args.goal,
                inputs,
                args.artifact,
                args.model,
                args.max_steps,
                args.handoff,
            )
        )
    except Exception as exc:
        result = Result(
            status="failure",
            code="policy_blocked"
            if isinstance(exc, PermissionError)
            else "execution_error",
        )
        if hasattr(surface, "page"):
            try:
                obs = await surface.observe()
                audit.snapshot(obs["screen"], obs["controls"])
            except Exception:
                pass
        audit.event("execution_error", code=type(exc).__name__)
    finally:
        if result:
            if (
                result.status != "success"
                and not (audit.directory / "failure.snapshot.json").exists()
                and hasattr(surface, "page")
            ):
                try:
                    obs = await surface.observe()
                    audit.snapshot(obs["screen"], obs["controls"])
                except Exception:
                    pass
            audit.result(result)
        await surface.close()
        controller.close()
    # Explicit caller channel; outputs never copied to persisted evidence.
    print(result.model_dump_json(indent=2))
    return 1 if result.status == "failure" else 0


def main():
    p = argparse.ArgumentParser(
        description="Discover and replay a bounded UI capability"
    )
    p.add_argument("command", choices=["discover", "replay"])
    p.add_argument("--target", default="http://127.0.0.1:8765/")
    p.add_argument("--policy", default="config/policy.json")
    p.add_argument("--artifact", required=True)
    p.add_argument("--inputs", required=True)
    p.add_argument("--run-dir", required=True)
    p.add_argument("--headed", action="store_true")
    p.add_argument("--handoff", action="store_true")
    p.add_argument(
        "--goal",
        default="Find the member identified by member_id. Prepare a new savings sub-account using nickname. Stop at review.",
    )
    p.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4.1"))
    p.add_argument("--max-steps", type=int, default=20)
    args = p.parse_args()
    if args.handoff and not args.headed:
        p.error("--handoff requires --headed for manual browser control")
    raise SystemExit(asyncio.run(execute(args)))


if __name__ == "__main__":
    main()
