"""Contract test: the SDK's REST operations and models against the vendored OpenAPI spec.

Every public function in `zerobull._operations.<area>` is called once with valid
dummy arguments to build a representative `Operation`, then checked against
`tests/fixtures/openapi.json`: the REST route exists, every field the SDK sends
is documented, and the response model's fields match the documented response
schema (unwrapping `data` and paginated items as needed).
"""

from __future__ import annotations

import datetime as dt
import inspect
import json
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Union, get_args, get_origin

import pytest
from pydantic import BaseModel

from zerobull._operations import (
    accounts,
    billing,
    phones,
    runs,
    session,
    submissions,
    uploads,
    user,
)
from zerobull._operations._base import Operation, RestRequest, compact
from zerobull.models.accounts import Account
from zerobull.models.billing import BillingRequest, BillingSummary, PhoneCountChange, Rental
from zerobull.models.phones import Phone
from zerobull.models.runs import Run
from zerobull.models.session import ControllerSession
from zerobull.models.submissions import Submission
from zerobull.models.uploads import UploadURL
from zerobull.models.user import User

SPEC: dict[str, Any] = json.loads((Path(__file__).parent / "fixtures" / "openapi.json").read_text())
PATHS: dict[str, dict[str, Any]] = SPEC["paths"]
COMPONENTS: dict[str, dict[str, Any]] = SPEC["components"]["schemas"]

ResponseShape = Literal["unwrapped", "wrapped", "wrapped_list", "page"]


# --- spec helpers -----------------------------------------------------------


def _resolve(schema: dict[str, Any]) -> dict[str, Any]:
    """Resolve a `$ref` against `components.schemas`."""
    while "$ref" in schema:
        schema = COMPONENTS[schema["$ref"].rsplit("/", 1)[-1]]
    return schema


def _find_spec_path(method: str, path: str) -> dict[str, Any]:
    """Match a concrete method and path to a spec operation by path segment."""
    actual = path.strip("/").split("/")
    for template, methods in PATHS.items():
        operation: dict[str, Any] | None = methods.get(method.lower())
        if operation is None:
            continue
        parts = template.strip("/").split("/")
        if len(parts) != len(actual):
            continue
        pairs = zip(parts, actual, strict=True)
        if all(part.startswith("{") or part == segment for part, segment in pairs):
            return operation
    raise AssertionError(f"no spec route matches {method} {path}")


def _documented_query_params(spec_op: dict[str, Any]) -> set[str]:
    return {p["name"] for p in spec_op.get("parameters", []) if p.get("in") == "query"}


def _documented_body_properties(spec_op: dict[str, Any]) -> set[str]:
    request_body = spec_op.get("requestBody")
    if not request_body:
        return set()
    properties: set[str] = set()
    for content in request_body.get("content", {}).values():
        properties |= set(_resolve(content["schema"]).get("properties", {}))
    return properties


def _response_schemas(spec_op: dict[str, Any], shape: ResponseShape) -> list[dict[str, Any]]:
    """Every success-status response schema, unwrapped per `shape`."""
    schemas: list[dict[str, Any]] = []
    for status, response in spec_op.get("responses", {}).items():
        if not status.isdigit() or int(status) >= 300:
            continue
        body = response.get("content", {}).get("application/json")
        if body is None:
            continue
        schema = _resolve(body["schema"])
        if shape == "unwrapped":
            schemas.append(schema)
        elif shape == "wrapped":
            schemas.append(_resolve(schema["properties"]["data"]))
        else:
            data_schema = _resolve(schema["properties"]["data"])
            schemas.append(_resolve(data_schema["items"]))
    return schemas


def _spec_types(schema: dict[str, Any]) -> tuple[set[str], bool]:
    """JSON types a schema allows, and whether it allows null. Handles `anyOf`."""
    schema = _resolve(schema)
    json_types: set[str] = set()
    nullable = False
    raw = schema.get("type")
    if isinstance(raw, list):
        for entry in raw:
            nullable = nullable or entry == "null"
            if entry != "null":
                json_types.add(entry)
    elif isinstance(raw, str):
        json_types.add(raw)
    for branch in schema.get("anyOf", []):
        branch_types, branch_nullable = _spec_types(branch)
        json_types |= branch_types
        nullable = nullable or branch_nullable
    return json_types, nullable


def _merged_field(name: str, schemas: list[dict[str, Any]]) -> tuple[set[str], bool, bool]:
    """A field's allowed types, nullability, and whether every schema requires it."""
    json_types: set[str] = set()
    nullable = False
    always_required = True
    for schema in schemas:
        resolved = _resolve(schema)
        properties = resolved.get("properties", {})
        if name not in properties:
            always_required = False
            continue
        field_types, field_nullable = _spec_types(properties[name])
        json_types |= field_types
        nullable = nullable or field_nullable
        if name not in resolved.get("required", []):
            always_required = False
    return json_types, nullable, always_required


# --- python/pydantic type helpers -------------------------------------------

_PRIMITIVES: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    dt.datetime: "string",
}


def _python_types(annotation: object) -> tuple[set[str], bool]:
    """JSON types a model field's annotation maps to, and whether it is nullable."""
    origin = get_origin(annotation)
    if origin in (Union, types.UnionType):
        args = get_args(annotation)
        nullable = type(None) in args
        rest = [arg for arg in args if arg is not type(None)]
        assert len(rest) == 1, f"unsupported union annotation: {annotation!r}"
        inner_types, _ = _python_types(rest[0])
        return inner_types, nullable
    if origin is list:
        return {"array"}, False
    if origin is dict:
        return {"object"}, False
    if annotation in _PRIMITIVES:
        return {_PRIMITIVES[annotation]}, False
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return {"object"}, False
    raise AssertionError(f"unsupported field annotation: {annotation!r}")


def _check_model(model_cls: type[BaseModel], schemas: list[dict[str, Any]]) -> None:
    """Check a model's fields against the union of one or more response schemas."""
    documented: set[str] = set()
    required: set[str] = set()
    for schema in schemas:
        resolved = _resolve(schema)
        documented |= set(resolved.get("properties", {}))
        required |= set(resolved.get("required", []))

    for name in model_cls.model_fields:
        assert name in documented, f"{model_cls.__name__}.{name} is not a documented response field"

    for name in required:
        assert name in model_cls.model_fields, (
            f"{model_cls.__name__} is missing required field {name!r}"
        )

    for name, field in model_cls.model_fields.items():
        if name not in documented:
            continue
        spec_type_set, spec_nullable, always_required = _merged_field(name, schemas)
        annotation = field.annotation
        assert annotation is not None
        model_type_set, model_nullable = _python_types(annotation)
        assert model_type_set <= spec_type_set, (
            f"{model_cls.__name__}.{name}: type {model_type_set} incompatible with "
            f"spec type {spec_type_set}"
        )
        if model_nullable:
            assert spec_nullable or not always_required, (
                f"{model_cls.__name__}.{name} is optional but the spec always requires it non-null"
            )


# --- request helpers ---------------------------------------------------------


def _sent_query_keys(rest: RestRequest) -> set[str]:
    return set(compact(rest.params))


def _sent_body_keys(rest: RestRequest) -> set[str]:
    if rest.data is not None:
        return set(compact(rest.data)) | set((rest.files or {}).keys())
    if rest.json is not None:
        body = compact(rest.json) if rest.compact_json else dict(rest.json)
        return set(body)
    return set()


# --- operations under test ---------------------------------------------------


@dataclass(frozen=True)
class Case:
    """One representative call to a public operation function."""

    name: str
    op: Operation[Any]
    model: type[BaseModel] | None = None
    shape: ResponseShape | None = None


ACCOUNT_ID = "11111111-1111-1111-1111-111111111111"
RUN_ID = "22222222-2222-2222-2222-222222222222"
BILLING_REQUEST_ID = "33333333-3333-3333-3333-333333333333"
SLOT = "slot-1"

CASES: list[Case] = [
    Case("accounts.list", accounts.list(page=1, platform="tiktok"), Account, "page"),
    Case("accounts.get", accounts.get(ACCOUNT_ID), Account, "wrapped"),
    Case(
        "accounts.create",
        accounts.create(
            handle="@me", platform="youtube", slot=SLOT, notes="note", google_email="a@example.com"
        ),
        Account,
        "wrapped",
    ),
    Case(
        "accounts.update",
        accounts.update(
            ACCOUNT_ID, handle="@new", slot=SLOT, notes="note", google_email="a@example.com"
        ),
        Account,
        "wrapped",
    ),
    Case("accounts.delete", accounts.delete(ACCOUNT_ID)),
    Case("billing.summary", billing.summary(), BillingSummary, "unwrapped"),
    Case(
        "billing.start_rental",
        billing.start_rental(accept_terms=True, phones=5, country="US"),
        Rental,
        "unwrapped",
    ),
    Case(
        "billing.request_phone_count",
        billing.request_phone_count(accept_terms=True, phones=5),
        PhoneCountChange,
        "unwrapped",
    ),
    Case(
        "billing.get_request", billing.get_request(BILLING_REQUEST_ID), BillingRequest, "unwrapped"
    ),
    Case("phones.list", phones.list(), Phone, "wrapped_list"),
    Case("phones.snapshot", phones.snapshot(SLOT, width=600)),
    Case("phones.ocr", phones.ocr(SLOT, width=600)),
    Case("phones.tap", phones.tap(SLOT, fx=0.5, fy=0.5)),
    Case("phones.swipe", phones.swipe(SLOT, fx1=0.1, fy1=0.1, fx2=0.9, fy2=0.9, steps=10)),
    Case("phones.hotkey", phones.hotkey(SLOT, "home")),
    Case("phones.type", phones.type(SLOT, "hello")),
    Case("phones.run_command", phones.run_command(SLOT, "brightness", level=0.5), Run, "wrapped"),
    Case(
        "phones.run_macro",
        phones.run_macro(SLOT, workflow="post-to-story", params={"caption": "hi"}),
        Run,
        "wrapped",
    ),
    Case("phones.run_agent", phones.run_agent(SLOT, "open settings"), Run, "wrapped"),
    Case("runs.list", runs.list(SLOT, page=1), Run, "page"),
    Case("runs.get", runs.get(SLOT, RUN_ID), Run, "wrapped"),
    Case("session.create", session.create(), ControllerSession, "unwrapped"),
    Case("submissions.list", submissions.list(page=1, platform="tiktok"), Submission, "page"),
    Case("submissions.get", submissions.get(123), Submission, "wrapped"),
    Case(
        "submissions.create",
        submissions.create(
            account_id=ACCOUNT_ID,
            platform="tiktok",
            video_url="https://example.com/video.mp4",
            caption="hi",
            draft=False,
        ),
        Submission,
        "wrapped",
    ),
    Case("submissions.cancel", submissions.cancel(123), Submission, "wrapped"),
    Case("submissions.delete", submissions.delete(123)),
    Case("uploads.create", uploads.create(), UploadURL, "unwrapped"),
    Case("user.get", user.get(), User, "wrapped"),
]

CASE_IDS = [case.name for case in CASES]
MODEL_CASES = [case for case in CASES if case.model is not None]
MODEL_CASE_IDS = [case.name for case in MODEL_CASES]

AREA_MODULES = (accounts, billing, phones, runs, session, submissions, uploads, user)


def _public_operations(module: types.ModuleType) -> set[str]:
    area = module.__name__.rsplit(".", 1)[-1]
    return {
        f"{area}.{name}"
        for name, value in vars(module).items()
        if not name.startswith("_")
        and inspect.isfunction(value)
        and value.__module__ == module.__name__
    }


# --- tests --------------------------------------------------------------------


def test_every_public_operation_is_covered() -> None:
    """A new operation must be added to CASES deliberately."""
    covered = {case.name for case in CASES}
    actual = {name for module in AREA_MODULES for name in _public_operations(module)}
    assert covered == actual


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_route_is_documented(case: Case) -> None:
    rest = case.op.rest
    assert rest is not None, f"{case.name} has no REST request"
    _find_spec_path(rest.method, rest.path)


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_request_fields_are_documented(case: Case) -> None:
    rest = case.op.rest
    assert rest is not None
    spec_op = _find_spec_path(rest.method, rest.path)
    undocumented_query = _sent_query_keys(rest) - _documented_query_params(spec_op)
    undocumented_body = _sent_body_keys(rest) - _documented_body_properties(spec_op)
    assert not undocumented_query, f"{case.name}: undocumented query params {undocumented_query}"
    assert not undocumented_body, f"{case.name}: undocumented body fields {undocumented_body}"


@pytest.mark.parametrize("case", MODEL_CASES, ids=MODEL_CASE_IDS)
def test_response_model_matches_spec(case: Case) -> None:
    rest = case.op.rest
    assert rest is not None
    assert case.model is not None
    assert case.shape is not None
    spec_op = _find_spec_path(rest.method, rest.path)
    schemas = _response_schemas(spec_op, case.shape)
    assert schemas, f"{case.name}: no documented success response"
    _check_model(case.model, schemas)


def test_checker_flags_a_renamed_field() -> None:
    """A model field the spec doesn't document must fail the checker."""
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"id": {"type": "string"}, "platform": {"type": "string"}},
        "required": ["id", "platform"],
    }

    class _RenamedField(BaseModel):
        id: str
        platfrom: str

    with pytest.raises(AssertionError):
        _check_model(_RenamedField, [schema])
