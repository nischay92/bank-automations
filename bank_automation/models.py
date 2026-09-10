from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Inputs(Strict):
    member_id: str = Field(pattern=r"^\d{5}$")
    nickname: str = Field(min_length=1, max_length=30, pattern=r"^\S(?:.*\S)?$")


class Target(Strict):
    frame: Literal["Member workspace"] = "Member workspace"
    strategy: Literal["label", "role"]
    name: str
    role: Literal["button", "combobox", "textbox"] | None = None


class Step(Strict):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    action: Literal["click", "fill", "select"]
    target: Target
    input_ref: Literal["member_id", "nickname"] | None = None
    literal: Literal["savings"] | None = None
    precondition: str
    postcondition: str
    timeout_ms: int = Field(default=5000, ge=100, le=10000)

    @model_validator(mode="after")
    def valid_value(self):
        if self.action == "fill" and (
            self.input_ref is None or self.literal is not None
        ):
            raise ValueError("Fill must reference a declared input")
        if self.action == "select" and (
            self.literal != "savings" or self.input_ref is not None
        ):
            raise ValueError("Select accepts the declared savings literal")
        if self.action == "click" and (self.input_ref or self.literal):
            raise ValueError("Click has no value")
        return self


class OutputField(Strict):
    type: Literal["string", "boolean"]
    source: Literal["review.account_type", "review.nickname", "checkpoint"]
    sensitive: bool = False


class Capability(Strict):
    schema_version: Literal["1.0"] = "1.0"
    name: Literal["prepare_savings_subaccount"] = "prepare_savings_subaccount"
    version: Literal["1.0.0"] = "1.0.0"
    provenance: Literal["authored_example", "live_llm_discovery"]
    model: str | None = None
    application: Literal["northstar-training"] = "northstar-training"
    ui_version: Literal["1.0"] = "1.0"
    effect: Literal["prepare_only"] = "prepare_only"
    input_schema: dict = Field(default_factory=Inputs.model_json_schema)
    outputs: dict[str, OutputField] = Field(
        default_factory=lambda: {
            "account_type": OutputField(type="string", source="review.account_type"),
            "nickname": OutputField(
                type="string", source="review.nickname", sensitive=True
            ),
            "review_verified": OutputField(type="boolean", source="checkpoint"),
        }
    )
    outcome_rules: Literal["northstar-v1"] = "northstar-v1"
    success: Literal["review_matches_inputs"] = "review_matches_inputs"
    steps: list[Step] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def contracts(self):
        if self.input_schema != Inputs.model_json_schema():
            raise ValueError("Unsupported input contract")
        expected = {
            "account_type": ("string", "review.account_type", False),
            "nickname": ("string", "review.nickname", True),
            "review_verified": ("boolean", "checkpoint", False),
        }
        if {
            k: (v.type, v.source, v.sensitive) for k, v in self.outputs.items()
        } != expected:
            raise ValueError("Unsupported output contract")
        if len({s.id for s in self.steps}) != len(self.steps):
            raise ValueError("Duplicate step IDs")
        return self


class Decision(Strict):
    action: Literal["click", "fill", "select", "finish", "intervene"]
    target_ref: str | None = None
    input_ref: Literal["member_id", "nickname"] | None = None
    literal: Literal["savings"] | None = None
    reason_code: Literal[
        "navigate", "enter_input", "choose_type", "verify_goal", "blocked"
    ]


class Result(Strict):
    status: Literal["success", "business_outcome", "failure"]
    code: str
    step: str | None = None
    expected: str | None = None
    observed: str | None = None
    outputs: dict | None = None
