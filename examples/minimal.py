"""A deterministic, local-only example of proposal -> Gateway -> receipt."""

from __future__ import annotations

import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from fioos_core import (
    EffectGrant,
    LocalNoteAdapter,
    ProjectPolicy,
    RuntimeGateway,
    ToolRequest,
    admit_external_proposal,
)


def main() -> None:
    proposal = admit_external_proposal(
        {
            "proposal_id": "demo-proposal-1",
            "source_id": "deterministic-local-agent",
            "source_revision": "fixture-v1",
            "objective": "Record a bounded local note.",
            "requested_capabilities": ["workspace.note.append"],
            "requested_tools": ["note.append"],
            "metadata": {"purpose": "runnable demonstration"},
        }
    )
    if not proposal.accepted or proposal.proposal is None:
        raise SystemExit(f"Proposal rejected: {proposal.rejection_reasons}")

    with tempfile.TemporaryDirectory(prefix="fioos-public-core-") as temporary:
        workspace = Path(temporary)
        workspace_id = "demo-workspace"
        policy = ProjectPolicy(
            workspace_id=workspace_id,
            grants=frozenset(
                {EffectGrant("workspace.note.append", "note.append")}
            ),
        )
        adapter = LocalNoteAdapter(workspace_id=workspace_id, root=workspace)
        gateway = RuntimeGateway(policy=policy, adapter=adapter)

        # The controller, not the proposal, chooses this exact operation.
        allowed = gateway.execute(
            ToolRequest(
                request_id="demo-request-1",
                workspace_id=workspace_id,
                operation="note.append",
                capability="workspace.note.append",
                payload={"text": "A bounded effect passed through the Gateway."},
                identity_claim=proposal.proposal.source_id,
            )
        )
        denied = gateway.execute(
            ToolRequest(
                request_id="demo-request-2",
                workspace_id=workspace_id,
                operation="shell.execute",
                capability="process.execute",
                payload={"command": "echo not run"},
                identity_claim="self-asserted-admin",
            )
        )
        output = {
            "admission": {
                "accepted": proposal.accepted,
                "source_revision_status": proposal.source_revision_status,
                "authority_granted": proposal.authority_granted,
                "requested_tools": list(proposal.proposal.requested_tools),
            },
            "authorized_result": asdict(allowed),
            "unauthorized_result": asdict(denied),
            "note_file_exists": (workspace / "notes.jsonl").is_file(),
        }
        print(json.dumps(output, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
