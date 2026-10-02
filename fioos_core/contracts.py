"""Typed proposal, request, result, and bounded evidence contracts.

External proposal admission is deliberately non-authorizing. No function in
this module invokes an effect adapter or creates a ToolRequest from a proposal.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


MAX_TEXT_CHARS = 2_000
MAX_ITEMS = 16
MAX_METADATA_BYTES = 8_192
MAX_SERIALIZED_INPUT_BYTES = 320 * 1_024
MAX_STRING_LENGTH = 8_192
MAX_COLLECTION_ITEMS = 64
MAX_NESTING_DEPTH = 32
MAX_JSON_NODES = 4_096
_MAX_NUMBER_BITS = MAX_STRING_LENGTH * 3
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_AUTHORITY_KEYS = frozenset(
    {
        "admin",
        "approval",
        "approved",
        "authority",
        "authoritygranted",
        "autonomy",
        "autonomylevel",
        "execute",
        "executeimmediately",
        "humanapproved",
        "lease",
        "override",
        "overridepolicy",
        "permission",
        "privileged",
        "role",
        "territory",
        "trusted",
        "verified",
        "write",
    }
)
_PROPOSAL_FIELDS = frozenset(
    {
        "proposal_id",
        "source_id",
        "source_revision",
        "objective",
        "requested_capabilities",
        "requested_tools",
        "metadata",
    }
)
_REQUIRED_PROPOSAL_FIELDS = frozenset(
    {"proposal_id", "source_id", "source_revision", "objective"}
)


class EvidenceState(str, Enum):
    OBSERVED = "OBSERVED"
    UNKNOWN = "UNKNOWN"
    CONTRADICTORY = "CONTRADICTORY"


@dataclass(frozen=True)
class ExternalProposal:
    proposal_id: str
    source_id: str
    source_revision: str
    objective: str
    requested_capabilities: tuple[str, ...]
    requested_tools: tuple[str, ...]
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class Admission:
    accepted: bool
    proposal: ExternalProposal | None
    payload_sha256: str
    source_revision_status: str
    rejection_reasons: tuple[str, ...]
    trust_class: str = "UNTRUSTED_EXTERNAL"
    authority_granted: bool = False
    real_effect_allowed: bool = False


@dataclass(frozen=True)
class ToolRequest:
    request_id: str
    workspace_id: str
    operation: str
    capability: str
    payload: Mapping[str, Any]
    identity_claim: str | None = None


@dataclass(frozen=True)
class ToolResult:
    request_id: str
    request_sha256: str
    decision: str
    status: str
    effect_count: int | None
    effect_id: str | None
    evidence_state: EvidenceState
    evidence_ref: str | None
    reason: str | None


@dataclass(frozen=True)
class EvidenceAssertion:
    claim_id: str
    value: str | None
    source_ref: str | None
    state: EvidenceState


def _json_string_size(value: str) -> int:
    if str.__len__(value) > MAX_STRING_LENGTH:
        raise ValueError("STRING_TOO_LONG")
    try:
        return len(
            json.dumps(
                str.__str__(value), ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
        )
    except UnicodeEncodeError as error:
        raise ValueError("INVALID_UNICODE") from error


def _bounded_json_snapshot(value: Any) -> Any:
    """Copy bounded JSON data before serialization so later mutation cannot evade limits."""
    total_bytes = 0
    node_count = 0
    active_containers: set[int] = set()
    snapshot: Any = None
    stack: list[tuple[str, Any, Any, int]] = [("visit", value, None, 0)]

    def add_bytes(amount: int) -> None:
        nonlocal total_bytes
        total_bytes += amount
        if total_bytes > MAX_SERIALIZED_INPUT_BYTES:
            raise ValueError("INPUT_TOO_LARGE")

    def assign(copied: Any, destination: Any) -> None:
        nonlocal snapshot
        if destination is None:
            snapshot = copied
        else:
            destination[0][destination[1]] = copied

    while stack:
        action, current, destination, depth = stack.pop()
        if action == "leave":
            active_containers.remove(current)
            continue

        node_count += 1
        if node_count > MAX_JSON_NODES:
            raise ValueError("INPUT_TOO_COMPLEX")

        if current is None:
            add_bytes(4)
            copied = None
        elif current is True:
            add_bytes(4)
            copied = True
        elif current is False:
            add_bytes(5)
            copied = False
        elif isinstance(current, str):
            add_bytes(_json_string_size(current))
            copied = current
        elif isinstance(current, int):
            if int.bit_length(current) > _MAX_NUMBER_BITS:
                raise ValueError("NUMBER_TOO_LARGE")
            try:
                encoded_number = json.dumps(current, allow_nan=False)
            except (TypeError, ValueError) as error:
                raise ValueError("VALUE_NOT_JSON_COMPATIBLE") from error
            add_bytes(len(encoded_number))
            copied = current
        elif isinstance(current, float):
            try:
                encoded_number = json.dumps(current, allow_nan=False)
            except (TypeError, ValueError) as error:
                raise ValueError("VALUE_NOT_JSON_COMPATIBLE") from error
            add_bytes(len(encoded_number))
            copied = current
        elif isinstance(current, dict):
            item_count = dict.__len__(current)
            if item_count > MAX_COLLECTION_ITEMS:
                raise ValueError("COLLECTION_TOO_LARGE")
            next_depth = depth + 1
            if next_depth > MAX_NESTING_DEPTH:
                raise ValueError("INPUT_TOO_DEEP")
            identity = id(current)
            if identity in active_containers:
                raise ValueError("CYCLIC_JSON_INPUT")
            active_containers.add(identity)
            copied = {}
            assign(copied, destination)
            add_bytes(2 + max(0, item_count - 1))
            try:
                iterator = iter(dict.items(current))
                items = []
                for _ in range(MAX_COLLECTION_ITEMS + 1):
                    try:
                        items.append(next(iterator))
                    except StopIteration:
                        break
            except RuntimeError as error:
                raise ValueError("MUTATING_INPUT") from error
            if len(items) > MAX_COLLECTION_ITEMS:
                raise ValueError("COLLECTION_TOO_LARGE")
            if dict.__len__(current) != item_count or len(items) != item_count:
                raise ValueError("MUTATING_INPUT")
            prepared_items = []
            for key, child in items:
                if not isinstance(key, str):
                    raise ValueError("OBJECT_KEY_MUST_BE_STRING")
                node_count += 1
                if node_count > MAX_JSON_NODES:
                    raise ValueError("INPUT_TOO_COMPLEX")
                add_bytes(_json_string_size(key) + 1)
                copied[key] = None
                prepared_items.append((key, child))
            stack.append(("leave", identity, None, depth))
            for key, child in reversed(prepared_items):
                stack.append(("visit", child, (copied, key), next_depth))
            continue
        elif isinstance(current, (list, tuple)):
            item_count = (
                list.__len__(current)
                if isinstance(current, list)
                else tuple.__len__(current)
            )
            if item_count > MAX_COLLECTION_ITEMS:
                raise ValueError("COLLECTION_TOO_LARGE")
            next_depth = depth + 1
            if next_depth > MAX_NESTING_DEPTH:
                raise ValueError("INPUT_TOO_DEEP")
            identity = id(current)
            if identity in active_containers:
                raise ValueError("CYCLIC_JSON_INPUT")
            active_containers.add(identity)
            if isinstance(current, list):
                try:
                    items = [list.__getitem__(current, index) for index in range(item_count)]
                except IndexError as error:
                    raise ValueError("MUTATING_INPUT") from error
                if list.__len__(current) > MAX_COLLECTION_ITEMS:
                    raise ValueError("COLLECTION_TOO_LARGE")
            else:
                items = [tuple.__getitem__(current, index) for index in range(item_count)]
            copied = [None] * item_count
            assign(copied, destination)
            add_bytes(2 + max(0, item_count - 1))
            stack.append(("leave", identity, None, depth))
            for index, child in reversed(list(enumerate(items))):
                stack.append(("visit", child, (copied, index), next_depth))
            continue
        else:
            raise ValueError("VALUE_NOT_JSON_COMPATIBLE")

        assign(copied, destination)

    return snapshot


def canonical_json(value: Any) -> str:
    """Serialize bounded JSON deterministically using strict UTF-8-compatible strings."""
    snapshot = _bounded_json_snapshot(value)
    try:
        serialized = json.dumps(
            snapshot,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        serialized.encode("utf-8")
        return serialized
    except UnicodeEncodeError as error:
        raise ValueError("INVALID_UNICODE") from error
    except RecursionError as error:
        raise ValueError("INPUT_TOO_DEEP") from error
    except (TypeError, ValueError) as error:
        raise ValueError("VALUE_NOT_JSON_COMPATIBLE") from error


def _digest_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _clean_identifier(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field.upper()}_MUST_BE_STRING")
    candidate = value.strip()
    if not _IDENTIFIER.fullmatch(candidate):
        raise ValueError(f"{field.upper()}_INVALID")
    return candidate


def _clean_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field.upper()}_MUST_BE_STRING")
    candidate = value.strip()
    if (
        not candidate
        or len(candidate) > MAX_TEXT_CHARS
        or any(ord(char) < 32 for char in candidate)
    ):
        raise ValueError(f"{field.upper()}_INVALID")
    return candidate


def _clean_items(value: Any, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        raise ValueError(f"{field.upper()}_MUST_BE_ARRAY")
    if len(value) > MAX_ITEMS:
        raise ValueError(f"{field.upper()}_TOO_MANY_ITEMS")
    return tuple(_clean_text(item, field) for item in value)


def _normalized_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _find_authority_keys(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _normalized_key(key) in _AUTHORITY_KEYS
            or _find_authority_keys(child)
            for key, child in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_find_authority_keys(child) for child in value)
    return False


def admit_external_proposal(payload: Mapping[str, Any]) -> Admission:
    """Validate external data while keeping provenance declared and unverified."""
    if not isinstance(payload, Mapping):
        return Admission(
            False, None, "0" * 64, "UNKNOWN", ("PAYLOAD_MUST_BE_OBJECT",)
        )
    try:
        canonical_input = canonical_json(payload)
        raw = json.loads(canonical_input)
        payload_digest = _digest_json(raw)
    except ValueError as error:
        return Admission(False, None, "0" * 64, "UNKNOWN", (str(error),))

    if _find_authority_keys(raw):
        return Admission(
            False,
            None,
            payload_digest,
            "DECLARED_UNVERIFIED",
            ("AUTHORITY_LIKE_FIELD_FORBIDDEN",),
        )

    unknown = sorted(set(raw) - _PROPOSAL_FIELDS)
    if unknown:
        return Admission(
            False,
            None,
            payload_digest,
            "DECLARED_UNVERIFIED",
            ("UNKNOWN_FIELD",),
        )
    if not _REQUIRED_PROPOSAL_FIELDS.issubset(raw):
        return Admission(
            False,
            None,
            payload_digest,
            "DECLARED_UNVERIFIED",
            ("REQUIRED_FIELD_MISSING",),
        )

    try:
        metadata = raw.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError("METADATA_MUST_BE_OBJECT")
        metadata_json = canonical_json(metadata)
        if len(metadata_json.encode("utf-8")) > MAX_METADATA_BYTES:
            raise ValueError("METADATA_TOO_LARGE")
        proposal = ExternalProposal(
            proposal_id=_clean_identifier(raw["proposal_id"], "proposal_id"),
            source_id=_clean_identifier(raw["source_id"], "source_id"),
            source_revision=_clean_identifier(
                raw["source_revision"], "source_revision"
            ),
            objective=_clean_text(raw["objective"], "objective"),
            requested_capabilities=_clean_items(
                raw.get("requested_capabilities"), "requested_capabilities"
            ),
            requested_tools=_clean_items(raw.get("requested_tools"), "requested_tools"),
            metadata=json.loads(metadata_json),
        )
    except (KeyError, ValueError) as error:
        return Admission(
            False,
            None,
            payload_digest,
            "DECLARED_UNVERIFIED",
            (str(error),),
        )

    return Admission(
        accepted=True,
        proposal=proposal,
        payload_sha256=payload_digest,
        source_revision_status="DECLARED_UNVERIFIED",
        rejection_reasons=(),
    )


def summarize_evidence(
    assertions: tuple[EvidenceAssertion, ...] | list[EvidenceAssertion],
) -> EvidenceState:
    """Summarize provenance states without promoting missing/conflicting data."""
    if type(assertions) not in (tuple, list):
        return EvidenceState.UNKNOWN
    if type(assertions) is list:
        item_count = list.__len__(assertions)
        if item_count > MAX_COLLECTION_ITEMS:
            return EvidenceState.UNKNOWN
        try:
            snapshot = tuple(
                list.__getitem__(assertions, index) for index in range(item_count)
            )
        except IndexError:
            return EvidenceState.UNKNOWN
        if list.__len__(assertions) != item_count:
            return EvidenceState.UNKNOWN
    else:
        snapshot = assertions
    if not snapshot:
        return EvidenceState.UNKNOWN
    if len(snapshot) > MAX_COLLECTION_ITEMS:
        return EvidenceState.UNKNOWN

    total_text_bytes = 0
    validated_assertions = []
    for assertion in snapshot:
        if type(assertion) is not EvidenceAssertion:
            return EvidenceState.UNKNOWN
        claim_id = assertion.claim_id
        value = assertion.value
        source_ref = assertion.source_ref
        state = assertion.state
        for field_value in (claim_id, value, source_ref):
            if field_value is None:
                continue
            if type(field_value) is not str:
                return EvidenceState.UNKNOWN
            try:
                total_text_bytes += _json_string_size(field_value)
            except ValueError:
                return EvidenceState.UNKNOWN
            if total_text_bytes > MAX_SERIALIZED_INPUT_BYTES:
                return EvidenceState.UNKNOWN
        validated_assertions.append((claim_id, value, source_ref, state))

    observed_values: dict[str, set[str]] = {}
    has_unknown = False
    for claim_id, value, source_ref, state in validated_assertions:
        if state is EvidenceState.CONTRADICTORY:
            return EvidenceState.CONTRADICTORY
        if (
            state is not EvidenceState.OBSERVED
            or not claim_id
            or type(value) is not str
            or not value
            or type(source_ref) is not str
            or not source_ref
        ):
            has_unknown = True
            continue
        observed_values.setdefault(claim_id, set()).add(value)

    if any(len(values) > 1 for values in observed_values.values()):
        return EvidenceState.CONTRADICTORY
    if has_unknown or not observed_values:
        return EvidenceState.UNKNOWN
    return EvidenceState.OBSERVED
