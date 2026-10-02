"""Single-process effect boundary for one fixed local note operation."""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Protocol

from .contracts import (
    EvidenceState,
    ToolRequest,
    ToolResult,
    _digest_json,
    canonical_json,
)
from .policy import ProjectPolicy


_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")


class EffectAdapter(Protocol):
    def perform(self, request: ToolRequest) -> str:
        """Perform the one bounded effect and return a relative evidence ref."""


class LocalNoteAdapter:
    """Append a JSON record to a fixed file under a trusted local workspace."""

    def __init__(self, *, workspace_id: str, root: Path | str) -> None:
        self.workspace_id = workspace_id
        self.root = Path(root).expanduser().resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("WORKSPACE_NOT_DIRECTORY")

    def perform(self, request: ToolRequest) -> str:
        if request.workspace_id != self.workspace_id:
            raise ValueError("ADAPTER_WORKSPACE_MISMATCH")
        if request.operation != "note.append":
            raise ValueError("ADAPTER_OPERATION_UNSUPPORTED")
        text = request.payload["text"]
        target = self.root / "notes.jsonl"
        if target.is_symlink():
            raise ValueError("NOTE_TARGET_SYMLINK_REJECTED")
        if target.exists() and not target.is_file():
            raise ValueError("NOTE_TARGET_NOT_FILE")
        record = {
            "request_id": request.request_id,
            "text": text,
        }
        with target.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            stream.write("\n")
        return "notes.jsonl"


class RuntimeGateway:
    """Mandatory intended path from typed request to the configured adapter.

    The in-memory ledger and lock cover one instance in one Python process.
    They are not a durable or distributed coordination mechanism.
    """

    def __init__(self, *, policy: ProjectPolicy, adapter: EffectAdapter) -> None:
        self._policy = policy
        self._adapter = adapter
        self._lock = threading.RLock()
        self._results: dict[str, tuple[str, ToolResult]] = {}

    def execute(self, request: ToolRequest) -> ToolResult:
        normalized, error, safe_request_id = self._snapshot_and_validate(request)
        if normalized is None:
            return self._denied(
                request_id=safe_request_id,
                request_digest="0" * 64,
                reason=error or "INVALID_REQUEST",
            )

        try:
            digest = _digest_json(
                {
                    "request_id": normalized.request_id,
                    "workspace_id": normalized.workspace_id,
                    "operation": normalized.operation,
                    "capability": normalized.capability,
                    "payload": dict(normalized.payload),
                    "identity_claim": normalized.identity_claim,
                }
            )
        except ValueError as error:
            reason = (
                "INVALID_REQUEST_ENCODING"
                if str(error) == "INVALID_UNICODE"
                else "INVALID_REQUEST"
            )
            return self._denied(
                request_id=normalized.request_id,
                request_digest="0" * 64,
                reason=reason,
            )
        with self._lock:
            previous = self._results.get(normalized.request_id)
            if previous is not None:
                previous_digest, previous_result = previous
                if previous_digest != digest:
                    return self._denied(
                        request_id=normalized.request_id,
                        request_digest=digest,
                        reason="REQUEST_ID_CONFLICT",
                    )
                return previous_result

            denial = self._policy.denial_reason(normalized)
            if denial is not None:
                result = self._denied(
                    request_id=normalized.request_id,
                    request_digest=digest,
                    reason=denial,
                )
                self._results[normalized.request_id] = (digest, result)
                return result

            if (
                normalized.operation != "note.append"
                or set(normalized.payload) != {"text"}
                or not isinstance(normalized.payload.get("text"), str)
                or not normalized.payload["text"].strip()
                or len(normalized.payload["text"]) > 2_000
                or any(ord(char) < 32 for char in normalized.payload["text"])
            ):
                result = self._denied(
                    request_id=normalized.request_id,
                    request_digest=digest,
                    reason="INVALID_EFFECT_PAYLOAD",
                )
                self._results[normalized.request_id] = (digest, result)
                return result

            try:
                evidence_ref = self._adapter.perform(normalized)
            except Exception:
                result = ToolResult(
                    request_id=normalized.request_id,
                    request_sha256=digest,
                    decision="ALLOW",
                    status="UNKNOWN",
                    effect_count=None,
                    effect_id=None,
                    evidence_state=EvidenceState.UNKNOWN,
                    evidence_ref=None,
                    reason="EFFECT_OUTCOME_UNKNOWN",
                )
            else:
                result = ToolResult(
                    request_id=normalized.request_id,
                    request_sha256=digest,
                    decision="ALLOW",
                    status="SUCCEEDED",
                    effect_count=1,
                    effect_id=f"effect:{normalized.request_id}",
                    evidence_state=EvidenceState.OBSERVED,
                    evidence_ref=evidence_ref,
                    reason=None,
                )
            self._results[normalized.request_id] = (digest, result)
            return result

    @staticmethod
    def _snapshot_and_validate(
        request: ToolRequest,
    ) -> tuple[ToolRequest | None, str | None, str]:
        if type(request) is not ToolRequest:
            return None, "INVALID_REQUEST_TYPE", ""
        try:
            request_id = object.__getattribute__(request, "request_id")
            workspace_id = object.__getattribute__(request, "workspace_id")
            operation = object.__getattribute__(request, "operation")
            capability = object.__getattribute__(request, "capability")
            payload_source = object.__getattribute__(request, "payload")
            identity_claim = object.__getattribute__(request, "identity_claim")
        except AttributeError:
            return None, "INVALID_REQUEST", ""
        if type(request_id) is not str or not _IDENTIFIER.fullmatch(request_id):
            return None, "INVALID_REQUEST", ""
        safe_request_id = request_id
        if type(workspace_id) is not str or not _IDENTIFIER.fullmatch(workspace_id):
            return None, "INVALID_REQUEST", safe_request_id
        if type(operation) is not str or not _IDENTIFIER.fullmatch(operation):
            return None, "INVALID_REQUEST", safe_request_id
        if type(capability) is not str or not _IDENTIFIER.fullmatch(capability):
            return None, "INVALID_REQUEST", safe_request_id
        if identity_claim is not None and (
            type(identity_claim) is not str or len(identity_claim) > 256
        ):
            return None, "INVALID_REQUEST", safe_request_id
        if not isinstance(payload_source, dict):
            return None, "INVALID_REQUEST", safe_request_id
        try:
            payload = json.loads(canonical_json(payload_source))
        except ValueError:
            return None, "INVALID_REQUEST_PAYLOAD", safe_request_id
        return (
            ToolRequest(
                request_id=request_id,
                workspace_id=workspace_id,
                operation=operation,
                capability=capability,
                payload=payload,
                identity_claim=identity_claim,
            ),
            None,
            safe_request_id,
        )

    @staticmethod
    def _denied(
        *,
        request_id: str,
        request_digest: str,
        reason: str,
    ) -> ToolResult:
        return ToolResult(
            request_id=request_id,
            request_sha256=request_digest,
            decision="DENY",
            status="DENIED",
            effect_count=0,
            effect_id=None,
            evidence_state=EvidenceState.OBSERVED,
            evidence_ref=None,
            reason=reason,
        )
