from __future__ import annotations

from collections.abc import Mapping as MappingABC
import unittest

from fioos_core import (
    EvidenceAssertion,
    EvidenceState,
    admit_external_proposal,
    summarize_evidence,
)
from fioos_core.contracts import (
    MAX_COLLECTION_ITEMS,
    MAX_JSON_NODES,
    MAX_NESTING_DEPTH,
    MAX_SERIALIZED_INPUT_BYTES,
    MAX_STRING_LENGTH,
    canonical_json,
)


def valid_proposal(**updates):
    value = {
        "proposal_id": "proposal-1",
        "source_id": "agent-example",
        "source_revision": "declared-r1",
        "objective": "Inspect a bounded local issue.",
        "requested_capabilities": ["workspace.note.append"],
        "requested_tools": ["note.append"],
        "metadata": {},
    }
    value.update(updates)
    return value


class ProposalContractTests(unittest.TestCase):
    def test_proposal_does_not_grant_authority_or_capabilities(self):
        admission = admit_external_proposal(valid_proposal())

        self.assertTrue(admission.accepted)
        self.assertFalse(admission.authority_granted)
        self.assertFalse(admission.real_effect_allowed)
        self.assertEqual(admission.trust_class, "UNTRUSTED_EXTERNAL")
        self.assertEqual(
            admission.source_revision_status, "DECLARED_UNVERIFIED"
        )
        self.assertEqual(
            admission.proposal.requested_capabilities,
            ("workspace.note.append",),
        )
        self.assertEqual(admission.proposal.requested_tools, ("note.append",))

    def test_mission_content_cannot_self_authorize(self):
        admission = admit_external_proposal(
            valid_proposal(
                metadata={"review": {"human": {"approved": True, "role": "admin"}}}
            )
        )

        self.assertFalse(admission.accepted)
        self.assertFalse(admission.authority_granted)
        self.assertIn("AUTHORITY_LIKE_FIELD_FORBIDDEN", admission.rejection_reasons)

    def test_unknown_top_level_field_is_rejected(self):
        admission = admit_external_proposal(valid_proposal(authority="A0"))

        self.assertFalse(admission.accepted)
        self.assertIn("AUTHORITY_LIKE_FIELD_FORBIDDEN", admission.rejection_reasons)

    def test_evidence_unknown_is_not_promoted(self):
        result = summarize_evidence(
            [EvidenceAssertion("claim-a", None, None, EvidenceState.UNKNOWN)]
        )

        self.assertIs(result, EvidenceState.UNKNOWN)

    def test_evidence_conflict_is_not_promoted(self):
        result = summarize_evidence(
            [
                EvidenceAssertion(
                    "claim-a", "yes", "receipt:1", EvidenceState.OBSERVED
                ),
                EvidenceAssertion(
                    "claim-a", "no", "receipt:2", EvidenceState.OBSERVED
                ),
            ]
        )

        self.assertIs(result, EvidenceState.CONTRADICTORY)

    def test_missing_evidence_is_unknown(self):
        self.assertIs(summarize_evidence([]), EvidenceState.UNKNOWN)

    def test_evidence_rejects_invalid_fields_and_malformed_unicode(self):
        class UnhashableString(str):
            __hash__ = None

        cases = (
            EvidenceAssertion(7, "yes", "receipt:1", EvidenceState.OBSERVED),
            EvidenceAssertion(
                ["claim-a"], "yes", "receipt:1", EvidenceState.OBSERVED
            ),
            EvidenceAssertion(
                UnhashableString("claim-a"),
                "yes",
                "receipt:1",
                EvidenceState.OBSERVED,
            ),
            EvidenceAssertion("claim-a", "yes", 9, EvidenceState.OBSERVED),
            EvidenceAssertion(
                "claim-a", "\ud800", "receipt:1", EvidenceState.OBSERVED
            ),
        )

        for assertion in cases:
            with self.subTest(assertion=type(assertion.value).__name__):
                self.assertIs(
                    summarize_evidence([assertion]), EvidenceState.UNKNOWN
                )

    def test_evidence_aggregation_enforces_collection_and_text_limits(self):
        too_many = [
            EvidenceAssertion(
                f"claim-{index}", "yes", f"receipt:{index}", EvidenceState.OBSERVED
            )
            for index in range(MAX_COLLECTION_ITEMS + 1)
        ]
        too_long = [
            EvidenceAssertion(
                "claim-a",
                "x" * (MAX_STRING_LENGTH + 1),
                "receipt:1",
                EvidenceState.OBSERVED,
            )
        ]
        aggregate_too_large = [
            EvidenceAssertion(
                "claim-a", "x" * MAX_STRING_LENGTH, "receipt:1", EvidenceState.OBSERVED
            )
            for _ in range(MAX_COLLECTION_ITEMS)
        ]

        for assertions in (too_many, too_long, aggregate_too_large):
            with self.subTest(assertion_count=len(assertions)):
                self.assertIs(summarize_evidence(assertions), EvidenceState.UNKNOWN)

    def test_evidence_rejects_custom_iterables_without_inspecting_them(self):
        class HostileIterable:
            def __bool__(self):
                raise AssertionError("must not evaluate custom truthiness")

            def __iter__(self):
                raise AssertionError("must not iterate custom input")

        self.assertIs(
            summarize_evidence(HostileIterable()), EvidenceState.UNKNOWN
        )

    def test_malformed_unicode_is_rejected_in_proposal_and_nested_metadata(self):
        for codepoint in (0xD800, 0xDC00):
            malformed = chr(codepoint)
            with self.subTest(codepoint=codepoint):
                direct = admit_external_proposal(
                    valid_proposal(objective=f"invalid {malformed}")
                )
                nested = admit_external_proposal(
                    valid_proposal(metadata={"nested": [{"value": malformed}]})
                )

                self.assertFalse(direct.accepted)
                self.assertIn("INVALID_UNICODE", direct.rejection_reasons)
                self.assertFalse(nested.accepted)
                self.assertIn("INVALID_UNICODE", nested.rejection_reasons)

    def test_valid_unicode_proposal_digest_is_stable_without_normalization(self):
        for text in ("plain ASCII", "caf\u00e9", "emoji \U0001f642", "e\u0301"):
            with self.subTest(text=text):
                proposal = valid_proposal(objective=text)
                reordered = dict(reversed(list(proposal.items())))
                first = admit_external_proposal(proposal)
                second = admit_external_proposal(reordered)

                self.assertTrue(first.accepted)
                self.assertEqual(first.payload_sha256, second.payload_sha256)


class BoundedCanonicalJsonTests(unittest.TestCase):
    @staticmethod
    def _array_with_encoded_size(target_bytes):
        item_count = 40
        framing_bytes = (2 + item_count - 1) + (2 * item_count)
        content_bytes = target_bytes - framing_bytes
        full_items = item_count - 1
        lengths = [MAX_STRING_LENGTH] * full_items
        lengths.append(content_bytes - (full_items * MAX_STRING_LENGTH))
        if any(length < 0 or length > MAX_STRING_LENGTH for length in lengths):
            raise AssertionError("test fixture does not fit per-string bounds")
        return ["x" * length for length in lengths]

    def test_serialized_byte_limit_just_below_at_and_above(self):
        for target in (MAX_SERIALIZED_INPUT_BYTES - 1, MAX_SERIALIZED_INPUT_BYTES):
            with self.subTest(target=target):
                serialized = canonical_json(self._array_with_encoded_size(target))
                self.assertEqual(len(serialized.encode("utf-8")), target)

        with self.assertRaisesRegex(ValueError, "INPUT_TOO_LARGE"):
            canonical_json(
                self._array_with_encoded_size(MAX_SERIALIZED_INPUT_BYTES + 1)
            )

    def test_string_limit_just_below_at_and_above(self):
        self.assertEqual(len(canonical_json("x" * (MAX_STRING_LENGTH - 1))), MAX_STRING_LENGTH + 1)
        self.assertEqual(len(canonical_json("x" * MAX_STRING_LENGTH)), MAX_STRING_LENGTH + 2)
        with self.assertRaisesRegex(ValueError, "STRING_TOO_LONG"):
            canonical_json("x" * (MAX_STRING_LENGTH + 1))

    def test_collection_limit_just_below_at_and_above(self):
        canonical_json([None] * (MAX_COLLECTION_ITEMS - 1))
        canonical_json([None] * MAX_COLLECTION_ITEMS)
        with self.assertRaisesRegex(ValueError, "COLLECTION_TOO_LARGE"):
            canonical_json([None] * (MAX_COLLECTION_ITEMS + 1))

    def test_nesting_limit_just_below_at_and_above(self):
        def nested(depth):
            value = None
            for _ in range(depth):
                value = [value]
            return value

        canonical_json(nested(MAX_NESTING_DEPTH - 1))
        canonical_json(nested(MAX_NESTING_DEPTH))
        with self.assertRaisesRegex(ValueError, "INPUT_TOO_DEEP"):
            canonical_json(nested(MAX_NESTING_DEPTH + 1))

    def test_total_node_limit_rejects_broad_nested_input(self):
        value = [[None] * MAX_COLLECTION_ITEMS for _ in range(MAX_COLLECTION_ITEMS)]
        with self.assertRaisesRegex(ValueError, "INPUT_TOO_COMPLEX"):
            canonical_json(value)

    def test_shared_subtrees_cannot_expand_past_node_limit(self):
        shared = [None] * MAX_COLLECTION_ITEMS
        value = [shared] * MAX_COLLECTION_ITEMS

        with self.assertRaisesRegex(ValueError, "INPUT_TOO_COMPLEX"):
            canonical_json(value)

    def test_cycles_are_rejected_as_typed_invalid_input(self):
        value = []
        value.append(value)

        with self.assertRaisesRegex(ValueError, "CYCLIC_JSON_INPUT"):
            canonical_json(value)

    def test_custom_mapping_is_rejected_without_iteration_or_length(self):
        class ExplosiveMapping(MappingABC):
            def __getitem__(self, key):
                raise AssertionError("custom mapping must not be read")

            def __iter__(self):
                raise AssertionError("custom mapping must not be iterated")

            def __len__(self):
                raise AssertionError("custom mapping length must not be read")

        admission = admit_external_proposal(ExplosiveMapping())

        self.assertFalse(admission.accepted)
        self.assertIn("VALUE_NOT_JSON_COMPATIBLE", admission.rejection_reasons)

    def test_non_string_object_key_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "OBJECT_KEY_MUST_BE_STRING"):
            canonical_json({1: "not a JSON object key"})

    def test_proposal_with_too_many_top_level_fields_is_rejected_early(self):
        payload = valid_proposal()
        payload.update(
            {f"extra-{index}": "x" for index in range(MAX_COLLECTION_ITEMS)}
        )

        admission = admit_external_proposal(payload)

        self.assertFalse(admission.accepted)
        self.assertIn("COLLECTION_TOO_LARGE", admission.rejection_reasons)


if __name__ == "__main__":
    unittest.main()
