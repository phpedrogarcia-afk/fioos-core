"""Controller-supplied A0 policy; identity and capability requests are not grants."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import ToolRequest


@dataclass(frozen=True)
class EffectGrant:
    capability: str
    operation: str


@dataclass(frozen=True)
class ProjectPolicy:
    """Trusted local configuration for this reference runtime.

    This class does not authenticate its constructor or prove that a human
    approved the supplied grants. The controller/operator must protect it.
    """

    workspace_id: str
    grants: frozenset[EffectGrant]
    autonomy_level: str = "A0"

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_id, str) or not self.workspace_id.strip():
            raise ValueError("WORKSPACE_ID_REQUIRED")
        if self.autonomy_level != "A0":
            raise ValueError("ONLY_A0_POLICY_SUPPORTED")
        normalized = frozenset(self.grants)
        if any(
            not isinstance(grant, EffectGrant)
            or not grant.capability
            or not grant.operation
            for grant in normalized
        ):
            raise ValueError("EFFECT_GRANT_INVALID")
        object.__setattr__(self, "grants", normalized)

    def denial_reason(self, request: ToolRequest) -> str | None:
        if request.workspace_id != self.workspace_id:
            return "WORKSPACE_NOT_AUTHORIZED"
        if EffectGrant(request.capability, request.operation) not in self.grants:
            return "EFFECT_NOT_AUTHORIZED"
        return None
