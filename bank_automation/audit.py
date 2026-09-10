"""Allowlisted metadata only; never serialize arbitrary exception/model/page text."""

import json
from datetime import UTC, datetime
from pathlib import Path


class Audit:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "events.jsonl"
        if self.path.exists():
            raise ValueError("Choose a fresh run directory")

    def event(self, event, **fields):
        allowed = {
            "step",
            "action",
            "state",
            "expected",
            "code",
            "owner",
            "reason_code",
            "model",
            "response_id",
            "control",
            "source",
            "count",
        }
        row = {"time": datetime.now(UTC).isoformat(), "event": event}
        row.update({k: v for k, v in fields.items() if k in allowed})
        with self.path.open("a") as f:
            f.write(json.dumps(row) + "\n")

    def result(self, result):
        safe = result.model_dump(exclude={"outputs"})
        safe["outputs_persisted"] = False
        (self.directory / "result.json").write_text(json.dumps(safe, indent=2))

    def snapshot(self, state, controls):
        (self.directory / "failure.snapshot.json").write_text(
            json.dumps(
                {
                    "screen": state,
                    "controls": controls,
                    "values": "omitted",
                    "page_text": "omitted",
                },
                indent=2,
            )
        )
