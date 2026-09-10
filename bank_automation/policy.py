from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .models import Step, Strict

SCENARIOS = {
    "normal",
    "slow",
    "stuck",
    "expired",
    "denied",
    "ambiguous",
    "disabled",
    "drift",
    "blocked",
    "dialog",
    "review_mismatch",
}


class Policy(Strict):
    origin: str
    routes: list[str]
    actions: list[tuple[str, str, str]]

    @classmethod
    def load(cls, path):
        return cls.model_validate_json(Path(path).read_text())

    def allows_url(self, url):
        p = urlsplit(url)
        return (
            f"{p.scheme}://{p.netloc}" == self.origin
            and not p.username
            and not p.password
            and p.path in self.routes
            and not p.fragment
            and all(
                k == "scenario" and len(v) == 1 and v[0] in SCENARIOS
                for k, v in parse_qs(p.query, keep_blank_values=True).items()
            )
        )

    def check(self, step: Step, state: str, url: str):
        if (
            not self.allows_url(url)
            or (state, step.action, step.target.name) not in self.actions
        ):
            raise PermissionError("policy_blocked")
        if (
            step.action == "fill"
            and {"Member ID": "member_id", "Nickname": "nickname"}.get(step.target.name)
            != step.input_ref
        ):
            raise PermissionError("parameter_binding_blocked")
        if step.target.strategy == "role" and step.target.role not in (
            "button",
            "combobox",
            "textbox",
        ):
            raise PermissionError("target_blocked")
