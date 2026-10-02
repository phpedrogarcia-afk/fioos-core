from __future__ import annotations

import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import fioos_core.gateway as gateway_module
from fioos_core import (
    EffectGrant,
    EvidenceState,
    LocalNoteAdapter,
    ProjectPolicy,
    RuntimeGateway,
    ToolRequest,
)
from fioos_core.contracts import MAX_COLLECTION_ITEMS, MAX_NESTING_DEPTH, MAX_STRING_LENGTH


class RecordingAdapter:
    def __init__(self, result="notes.jsonl", raises=False):
        self.calls = []
        self.result = result
        self.raises = raises

    def perform(self, request):
        self.calls.append(request)
        if self.raises:
            raise RuntimeError("simulated ambiguous adapter outcome")
        return self.result


class AdversarialString(str):
    def __ne__(self, other):
        return False


class UnhashableString(str):
    __hash__ = None


class ToolRequestSubclass(ToolRequest):
    def __getattribute__(self, name):
        if name in {
            "request_id",
            "workspace_id",
            "operation",
            "capability",
            "payload",
            "identity_claim",
        }:
            raise AssertionError("rejected request attributes must not be read")
        return super().__getattribute__(name)


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.workspace_id = "test-workspace"
        self.policy = ProjectPolicy(
            workspace_id=self.workspace_id,
            grants=frozenset(
                {EffectGrant("workspace.note.append", "note.append")}
            ),
        )

    def request(self, **updates):
        values = {
            "request_id": "request-1",
            "workspace_id": self.workspace_id,
            "operation": "note.append",
            "capability": "workspace.note.append",
            "payload": {"text": "test note"},
            "identity_claim": None,
        }
        values.update(updates)
        return ToolRequest(**values)

    def test_authorized_effect_is_mediated_and_correlated(self):
        adapter = LocalNoteAdapter(
            workspace_id=self.workspace_id, root=self.workspace
        )
        gateway = RuntimeGateway(policy=self.policy, adapter=adapter)

        result = gateway.execute(self.request())
        records = [
            json.loads(line)
            for line in (self.workspace / "notes.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]

        self.assertEqual(result.status, "SUCCEEDED")
        self.assertEqual(result.decision, "ALLOW")
        self.assertEqual(result.request_id, "request-1")
        self.assertEqual(len(result.request_sha256), 64)
        self.assertEqual(result.effect_count, 1)
        self.assertEqual(result.effect_id, "effect:request-1")
        self.assertEqual(result.evidence_state, EvidenceState.OBSERVED)
        self.assertEqual(result.evidence_ref, "notes.jsonl")
        self.assertEqual(records[0]["request_id"], result.request_id)

    def test_unauthorized_effect_is_denied_before_adapter(self):
        adapter = RecordingAdapter()
        gateway = RuntimeGateway(policy=self.policy, adapter=adapter)

        result = gateway.execute(
            self.request(
                operation="filesystem.delete",
                capability="filesystem.delete",
                payload={"path": "notes.jsonl"},
            )
        )

        self.assertEqual(result.status, "DENIED")
        self.assertEqual(result.effect_count, 0)
        self.assertEqual(result.reason, "EFFECT_NOT_AUTHORIZED")
        self.assertEqual(adapter.calls, [])

    def test_string_subclasses_are_rejected_before_authorization(self):
        adapter = RecordingAdapter()
        gateway = RuntimeGateway(policy=self.policy, adapter=adapter)
        malformed_requests = (
            (
                self.request(workspace_id=AdversarialString("other-workspace")),
                "INVALID_REQUEST",
                "request-1",
            ),
            (
                self.request(operation=AdversarialString("note.append")),
                "INVALID_REQUEST",
                "request-1",
            ),
            (
                self.request(capability=AdversarialString("workspace.note.append")),
                "INVALID_REQUEST",
                "request-1",
            ),
            (
                self.request(identity_claim=AdversarialString("untrusted-claim")),
                "INVALID_REQUEST",
                "request-1",
            ),
            (
                self.request(request_id=UnhashableString("request-1")),
                "INVALID_REQUEST",
                "",
            ),
            (
                ToolRequestSubclass(**self.request().__dict__),
                "INVALID_REQUEST_TYPE",
                "",
            ),
        )

        for index, (request, expected_reason, expected_request_id) in enumerate(
            malformed_requests
        ):
            with self.subTest(index=index):
                result = gateway.execute(request)
                self.assertEqual(result.status, "DENIED")
                self.assertEqual(result.request_id, expected_request_id)
                self.assertEqual(result.effect_count, 0)
                self.assertEqual(result.reason, expected_reason)

        self.assertEqual(adapter.calls, [])

    def test_execution_uses_the_validated_scalar_snapshot(self):
        adapter = RecordingAdapter()
        gateway = RuntimeGateway(policy=self.policy, adapter=adapter)
        request = self.request()
        original_identifier = gateway_module._IDENTIFIER

        class MutatingIdentifier:
            def fullmatch(self, value):
                match = original_identifier.fullmatch(value)
                if value == self_workspace_id:
                    object.__setattr__(
                        request,
                        "workspace_id",
                        AdversarialString("other-workspace"),
                    )
                return match

        self_workspace_id = self.workspace_id
        with patch.object(gateway_module, "_IDENTIFIER", MutatingIdentifier()):
            result = gateway.execute(request)

        self.assertEqual(result.status, "SUCCEEDED")
        self.assertEqual(result.effect_count, 1)
        self.assertEqual(len(adapter.calls), 1)
        self.assertIs(type(adapter.calls[0].workspace_id), str)
        self.assertEqual(adapter.calls[0].workspace_id, self.workspace_id)

    def test_identity_claim_does_not_grant_authority(self):
        adapter = RecordingAdapter()
        gateway = RuntimeGateway(policy=self.policy, adapter=adapter)

        result = gateway.execute(
            self.request(
                operation="shell.execute",
                capability="process.execute",
                payload={"command": "echo not run"},
                identity_claim="signed-admin-root",
            )
        )

        self.assertEqual(result.status, "DENIED")
        self.assertEqual(result.effect_count, 0)
        self.assertEqual(adapter.calls, [])

    def test_shell_timeout_or_process_request_has_no_execution_path(self):
        adapter = RecordingAdapter()
        gateway = RuntimeGateway(policy=self.policy, adapter=adapter)

        result = gateway.execute(
            self.request(
                operation="process.execute",
                capability="process.execute",
                payload={"command": "sleep 60", "timeout_seconds": 1},
            )
        )

        self.assertEqual(result.status, "DENIED")
        self.assertEqual(result.effect_count, 0)
        self.assertEqual(adapter.calls, [])

    def test_same_instance_replay_returns_prior_result_without_second_effect(self):
        adapter = RecordingAdapter()
        gateway = RuntimeGateway(policy=self.policy, adapter=adapter)
        request = self.request()

        first = gateway.execute(request)
        replay = gateway.execute(request)

        self.assertEqual(first, replay)
        self.assertEqual(len(adapter.calls), 1)

    def test_request_id_conflict_does_not_invoke_adapter_again(self):
        adapter = RecordingAdapter()
        gateway = RuntimeGateway(policy=self.policy, adapter=adapter)

        first = gateway.execute(self.request())
        conflict = gateway.execute(
            self.request(payload={"text": "different body"})
        )

        self.assertEqual(first.status, "SUCCEEDED")
        self.assertEqual(conflict.reason, "REQUEST_ID_CONFLICT")
        self.assertEqual(len(adapter.calls), 1)

    def test_concurrent_same_instance_request_invokes_adapter_once(self):
        adapter = RecordingAdapter()
        gateway = RuntimeGateway(policy=self.policy, adapter=adapter)
        request = self.request()

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(gateway.execute, [request] * 8))

        self.assertTrue(all(result == results[0] for result in results))
        self.assertEqual(results[0].status, "SUCCEEDED")
        self.assertEqual(len(adapter.calls), 1)

    def test_adapter_ambiguity_remains_unknown_and_is_not_retried(self):
        adapter = RecordingAdapter(raises=True)
        gateway = RuntimeGateway(policy=self.policy, adapter=adapter)
        request = self.request()

        first = gateway.execute(request)
        replay = gateway.execute(request)

        self.assertEqual(first.status, "UNKNOWN")
        self.assertIsNone(first.effect_count)
        self.assertEqual(first.evidence_state, EvidenceState.UNKNOWN)
        self.assertEqual(first.reason, "EFFECT_OUTCOME_UNKNOWN")
        self.assertEqual(first, replay)
        self.assertEqual(len(adapter.calls), 1)

    def test_policy_rejects_non_a0_level(self):
        with self.assertRaisesRegex(ValueError, "ONLY_A0_POLICY_SUPPORTED"):
            ProjectPolicy(
                workspace_id=self.workspace_id,
                grants=frozenset(),
                autonomy_level="A1",
            )

    def test_oversized_deep_and_wide_payloads_deny_before_adapter(self):
        deep_payload = None
        for _ in range(MAX_NESTING_DEPTH + 1):
            deep_payload = [deep_payload]
        payloads = (
            {"text": "x" * (MAX_STRING_LENGTH + 1)},
            {"text": [None] * (MAX_COLLECTION_ITEMS + 1)},
            {"text": deep_payload},
        )
        adapter = RecordingAdapter()
        gateway = RuntimeGateway(policy=self.policy, adapter=adapter)

        for index, payload in enumerate(payloads):
            with self.subTest(index=index):
                result = gateway.execute(
                    self.request(request_id=f"bounded-{index}", payload=payload)
                )
                self.assertEqual(result.status, "DENIED")
                self.assertEqual(result.effect_count, 0)
                self.assertEqual(result.reason, "INVALID_REQUEST_PAYLOAD")

        self.assertEqual(adapter.calls, [])

    def test_malformed_unicode_payload_is_denied_without_effect(self):
        adapter = RecordingAdapter()
        gateway = RuntimeGateway(policy=self.policy, adapter=adapter)

        for index, codepoint in enumerate((0xD800, 0xDC00)):
            with self.subTest(codepoint=codepoint):
                result = gateway.execute(
                    self.request(
                        request_id=f"unicode-payload-{index}",
                        payload={"text": f"bad {chr(codepoint)}"},
                    )
                )

                self.assertEqual(result.status, "DENIED")
                self.assertEqual(result.effect_count, 0)
                self.assertEqual(result.reason, "INVALID_REQUEST_PAYLOAD")

        nested = gateway.execute(
            self.request(
                request_id="unicode-nested",
                payload={"text": {"nested": chr(0xD800)}},
            )
        )
        self.assertEqual(nested.status, "DENIED")
        self.assertEqual(nested.effect_count, 0)
        self.assertEqual(nested.reason, "INVALID_REQUEST_PAYLOAD")
        self.assertEqual(adapter.calls, [])

    def test_malformed_unicode_identity_claim_is_denied_without_effect(self):
        adapter = RecordingAdapter()
        gateway = RuntimeGateway(policy=self.policy, adapter=adapter)

        for index, codepoint in enumerate((0xD800, 0xDC00)):
            with self.subTest(codepoint=codepoint):
                result = gateway.execute(
                    self.request(
                        request_id=f"unicode-identity-{index}",
                        identity_claim=f"claim-{chr(codepoint)}",
                    )
                )

                self.assertEqual(result.status, "DENIED")
                self.assertEqual(result.effect_count, 0)
                self.assertEqual(result.reason, "INVALID_REQUEST_ENCODING")

        self.assertEqual(adapter.calls, [])

    def test_valid_unicode_request_digest_is_stable(self):
        adapter = RecordingAdapter()
        gateway = RuntimeGateway(policy=self.policy, adapter=adapter)

        for index, text in enumerate(("plain ASCII", "caf\u00e9", "emoji \U0001f642", "e\u0301")):
            with self.subTest(text=text):
                request = self.request(
                    request_id=f"valid-unicode-{index}", payload={"text": text}
                )
                first = gateway.execute(request)
                replay = gateway.execute(request)

                self.assertEqual(first.status, "SUCCEEDED")
                self.assertEqual(first, replay)
                self.assertEqual(len(first.request_sha256), 64)

        self.assertEqual(len(adapter.calls), 4)


if __name__ == "__main__":
    unittest.main()
