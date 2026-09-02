"""
Validation Service
Multi-Step Citation Verification & Claim-to-Evidence Grounding Engine.
Enforces that every LLM claim is backed by relevant, authorized, and actually retrieved evidence.
"""
from typing import Optional
from app.models.schemas import (
    Claim,
    ClaimSupportStatus,
    EvidenceChunk,
    UserRole
)
from app.services.permission_service import permission_service


class ValidationService:
    @staticmethod
    def validate_citations(
        claims: list[Claim],
        retrieved_evidence: list[EvidenceChunk],
        role: UserRole
    ) -> tuple[list[Claim], str, list[str], float]:
        """
        Validates every claim's evidence citations against retrieved and authorized evidence.
        Verifies entity and relationship alignment to prevent cross-entity citation fraud.
        
        Returns:
            - validated_claims: list of claims with verification flags updated
            - validation_status: "PASSED" | "WARNING" | "FAILED"
            - validation_checks: list of human-readable verification log messages
            - citation_validity_rate: float (0.0 to 1.0)
        """
        retrieved_ev_map: dict[str, EvidenceChunk] = {ev.id: ev for ev in retrieved_evidence}
        validation_checks: list[str] = []
        validated_claims: list[Claim] = []

        total_citations = 0
        valid_citations = 0
        unsupported_claims_count = 0

        for idx, claim in enumerate(claims, 1):
            claim_copy = claim.model_copy()
            
            # Case 1: Claim has no documentary citation
            if not claim.evidence_ids:
                if claim.support_status == ClaimSupportStatus.GRAPH_VERIFIED:
                    claim_copy.is_verified = False
                    claim_copy.unsupported_reason = "Verified in knowledge graph topology; no direct documentary citation."
                    validation_checks.append(f"ℹ️ Claim #{idx} is a verified Graph Fact (no documentary citation).")
                else:
                    claim_copy.is_verified = False
                    claim_copy.support_status = ClaimSupportStatus.UNSUPPORTED
                    claim_copy.unsupported_reason = "No citation provided for this claim."
                    validation_checks.append(f"⚠️ Claim #{idx} has no supporting citation.")
                    unsupported_claims_count += 1
                validated_claims.append(claim_copy)
                continue

            # Case 2: Claim cites evidence IDs -> Run rigorous multi-step checks
            all_claim_citations_valid = True
            invalid_reasons: list[str] = []

            for ev_id in claim.evidence_ids:
                total_citations += 1
                
                # Check 1: Was evidence retrieved in this query?
                if ev_id not in retrieved_ev_map:
                    all_claim_citations_valid = False
                    invalid_reasons.append(f"Evidence ID '{ev_id}' was not in retrieved context.")
                    continue

                ev_chunk = retrieved_ev_map[ev_id]

                # Check 2: Was evidence authorized for the user?
                if not permission_service.is_authorized(role, ev_chunk.classification):
                    all_claim_citations_valid = False
                    invalid_reasons.append(f"Evidence ID '{ev_id}' requires higher clearance ({ev_chunk.classification.value}).")
                    continue

                # Check 3: Entity Association Check (Cross-Entity Contamination Prevention)
                if claim.entities:
                    overlap = set(claim.entities).intersection(set(ev_chunk.relevant_entities))
                    if not overlap:
                        all_claim_citations_valid = False
                        invalid_reasons.append(f"Evidence '{ev_id}' ({', '.join(ev_chunk.relevant_entities)}) does not match claimed entities ({', '.join(claim.entities)}).")
                        continue

                valid_citations += 1

            if all_claim_citations_valid:
                claim_copy.is_verified = True
                claim_copy.support_status = ClaimSupportStatus.SUPPORTED
                claim_copy.unsupported_reason = None
                validation_checks.append(f"✓ Claim #{idx} verified against [{', '.join(claim.evidence_ids)}].")
            else:
                claim_copy.is_verified = False
                claim_copy.support_status = ClaimSupportStatus.UNSUPPORTED
                claim_copy.unsupported_reason = "; ".join(invalid_reasons)
                validation_checks.append(f"❌ Claim #{idx} citation check failed: {claim_copy.unsupported_reason}")
                unsupported_claims_count += 1

            validated_claims.append(claim_copy)

        validity_rate = (valid_citations / total_citations) if total_citations > 0 else (1.0 if not claims else 0.0)

        if unsupported_claims_count == 0 and total_citations > 0:
            status = "PASSED"
        elif unsupported_claims_count > 0 and valid_citations > 0:
            status = "WARNING"
        elif not claims:
            status = "PASSED"
        else:
            status = "FAILED"

        validation_checks.append(f"Citation verification complete: {valid_citations}/{total_citations} valid citations ({round(validity_rate * 100, 1)}%).")
        return validated_claims, status, validation_checks, validity_rate


validation_service = ValidationService()
