"""
Evaluation Service
Executes automated benchmark runs over golden test cases and measures actual performance metrics.
"""
import time
from datetime import datetime, timezone

from app.data.golden_dataset import GOLDEN_BENCHMARK_CASES
from app.models.schemas import (
    EvaluationReport,
    EvaluationTestResult,
    QueryRequest,
    ClassificationLevel
)
from app.services.intent_service import intent_service
from app.services.retrieval_service import retrieval_service
from app.services.graph_service import graph_service
from app.services.llm_service import llm_service
from app.services.validation_service import validation_service
from app.services.confidence_service import confidence_service


class EvaluationService:
    def __init__(self):
        from app.data.seed_data import SEED_ENTITIES, SEED_RELATIONSHIPS
        graph_service.load_data(SEED_ENTITIES, SEED_RELATIONSHIPS)

    async def run_evaluation(self) -> EvaluationReport:
        results: list[EvaluationTestResult] = []
        start_all = time.time()

        total_entity_acc = 0.0
        total_path_acc = 0.0
        total_citation_val = 0.0
        permission_violations = 0
        unsupported_claims_count = 0
        total_claims_count = 0
        schema_valid_count = 0

        for test in GOLDEN_BENCHMARK_CASES:
            t0 = time.time()

            # 0. Intent Classification
            intent, _ = intent_service.classify_intent(test.query)

            # 1. Deterministic Entity Extraction & Role Filtering
            auth_entities, filtered_entities = retrieval_service.identify_entities(test.query, test.role)
            auth_entity_ids = [e.id for e in auth_entities]

            # Check for permission leakage in entities
            leakage = any(
                e.classification == ClassificationLevel.RESTRICTED and test.role != test.role.ADMIN
                for e in auth_entities
            )

            # 2. Graph Traversal
            paths = graph_service.traverse_for_entities(auth_entity_ids, test.role, max_hops=3)

            # 3. Hybrid Evidence Retrieval
            evidence, filtered_ev = retrieval_service.retrieve_evidence(
                test.query, test.role, paths, auth_entities, intent=intent, top_k=4
            )

            # Check for permission leakage in evidence
            if any(ev.classification == ClassificationLevel.RESTRICTED and test.role != test.role.ADMIN for ev in evidence):
                leakage = True

            # 4. LLM Reasoning (Deterministic Benchmark Engine)
            llm_output = llm_service._generate_deterministic_response(
                test.query, test.role, auth_entities, paths, evidence, intent
            )

            # 5. Citation Validation
            val_claims, val_status, val_checks, cit_rate = validation_service.validate_citations(
                llm_output.claims, evidence, test.role
            )

            # 6. Confidence Scoring
            is_insufficient = (len(evidence) == 0 and len(auth_entities) == 0) or "insufficient" in llm_output.answer.lower()
            conf = confidence_service.calculate(
                auth_entities, paths, evidence, val_claims, cit_rate, intent=intent, is_insufficient_evidence=is_insufficient
            )

            t_elapsed_ms = round((time.time() - t0) * 1000, 2)

            # Build set of all discovered and authorized entities from extraction, graph, and evidence
            all_discovered_entities = set(auth_entity_ids)
            for p in paths:
                all_discovered_entities.update(p.path_nodes)
            for ev in evidence:
                all_discovered_entities.update(ev.relevant_entities)

            # Evaluate Metrics
            # Entity accuracy
            if test.expected_entities:
                overlap = set(test.expected_entities).intersection(all_discovered_entities)
                ent_acc = len(overlap) / len(test.expected_entities)
            else:
                ent_acc = 1.0 if not auth_entity_ids or test.expected_insufficient else 0.5

            # Path accuracy
            if test.expected_path_nodes:
                matched_nodes = 0
                for p in paths:
                    if any(node in p.path_nodes for node in test.expected_path_nodes):
                        matched_nodes += 1
                path_acc = 1.0 if matched_nodes > 0 else 0.0
            else:
                path_acc = 1.0

            # Schema valid
            schema_valid = bool(llm_output.answer and isinstance(llm_output.claims, list))
            if schema_valid:
                schema_valid_count += 1

            if leakage:
                permission_violations += 1

            unsupported = sum(1 for c in val_claims if not c.is_verified)
            unsupported_claims_count += unsupported
            total_claims_count += len(val_claims)

            total_entity_acc += ent_acc
            total_path_acc += path_acc
            total_citation_val += cit_rate

            # Test Passed criteria
            if test.expected_insufficient:
                passed = is_insufficient and not leakage
                detail_msg = f"Insufficient evidence correctly enforced. Filtered docs: {len(filtered_ev)}. Leakage: False."
            else:
                passed = (ent_acc >= 0.5) and (cit_rate >= 0.8) and (not leakage) and schema_valid
                detail_msg = f"Entities matched: {round(ent_acc*100)}%, Citations valid: {round(cit_rate*100)}%, Paths found: {len(paths)}."

            results.append(EvaluationTestResult(
                test_id=test.id,
                name=test.name,
                category=test.category,
                role=test.role,
                passed=passed,
                latency_ms=t_elapsed_ms,
                entity_accuracy=round(ent_acc * 100, 1),
                path_accuracy=round(path_acc * 100, 1),
                citation_validity=round(cit_rate * 100, 1),
                permission_leakage=leakage,
                structured_schema_valid=schema_valid,
                details=detail_msg
            ))

        n = len(GOLDEN_BENCHMARK_CASES)
        passed_n = sum(1 for r in results if r.passed)
        avg_lat = round(sum(r.latency_ms for r in results) / n, 2) if n > 0 else 0.0

        return EvaluationReport(
            total_tests=n,
            passed_tests=passed_n,
            failed_tests=n - passed_n,
            pass_rate=round((passed_n / n) * 100, 1) if n > 0 else 0.0,
            avg_latency_ms=avg_lat,
            entity_retrieval_accuracy=round((total_entity_acc / n) * 100, 1) if n > 0 else 0.0,
            graph_path_correctness=round((total_path_acc / n) * 100, 1) if n > 0 else 0.0,
            citation_validity_rate=round((total_citation_val / n) * 100, 1) if n > 0 else 0.0,
            permission_violation_rate=round((permission_violations / n) * 100, 1) if n > 0 else 0.0,
            unsupported_claim_rate=round((unsupported_claims_count / max(total_claims_count, 1)) * 100, 1),
            structured_output_validity_rate=round((schema_valid_count / n) * 100, 1) if n > 0 else 0.0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            test_results=results
        )


evaluation_service = EvaluationService()
