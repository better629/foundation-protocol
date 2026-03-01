"""Dispute primitives."""

from __future__ import annotations

from uuid import uuid4

from fp.protocol import Dispute


class DisputeService:
    def open(
        self,
        *,
        target_ref: str,
        reason_code: str,
        claimant_entity_id: str,
        evidence_refs: list[str] | None = None,
    ) -> Dispute:
        return Dispute(
            dispute_id=f"dsp-{uuid4().hex}",
            target_ref=target_ref,
            reason_code=reason_code,
            claimant_entity_id=claimant_entity_id,
            evidence_refs=evidence_refs or [],
        )

    def close(self, dispute: Dispute, *, status: str = "closed") -> Dispute:
        dispute.status = status
        return dispute
