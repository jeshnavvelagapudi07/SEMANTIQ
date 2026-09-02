"""
Golden Benchmark Evaluation Dataset for SEMANTIQ
Standardized evaluation queries, ground truth, expected graph paths, and security boundaries.
"""
from app.models.schemas import EvaluationTestCase, UserRole

GOLDEN_BENCHMARK_CASES: list[EvaluationTestCase] = [
    EvaluationTestCase(
        id="GOLDEN-01",
        name="Multi-Hop Incident Impact & Actions",
        query="Which projects are affected by Incident 104 and what should the responsible team do?",
        role=UserRole.OPERATIONS_ENGINEER,
        expected_entities=["INC-104", "PRJ-GAMMA", "PRJ-ALPHA", "SYS-CNC-07"],
        expected_doc_ids=["SOP-017", "DOC-031"],
        expected_path_nodes=["PRJ-GAMMA", "SYS-CNC-07", "INC-104"],
        expected_insufficient=False,
        category="Multi-Hop Reasoning"
    ),
    EvaluationTestCase(
        id="GOLDEN-02",
        name="Project Risk Chain Analysis",
        query="Why is Project C considered high risk?",
        role=UserRole.OPERATIONS_ENGINEER,
        expected_entities=["PRJ-GAMMA", "SYS-CNC-07", "INC-104", "SOP-017"],
        expected_doc_ids=["DOC-031", "SOP-017"],
        expected_path_nodes=["PRJ-GAMMA", "SYS-CNC-07", "INC-104"],
        expected_insufficient=False,
        category="Multi-Hop Reasoning"
    ),
    EvaluationTestCase(
        id="GOLDEN-03",
        name="Direct Equipment Dependency",
        query="Which projects depend on CNC-07?",
        role=UserRole.OPERATIONS_ENGINEER,
        expected_entities=["SYS-CNC-07", "PRJ-GAMMA", "PRJ-ALPHA"],
        expected_doc_ids=["DOC-031"],
        expected_path_nodes=["PRJ-GAMMA", "SYS-CNC-07"],
        expected_insufficient=False,
        category="Graph Retrieval"
    ),
    EvaluationTestCase(
        id="GOLDEN-04",
        name="SOP Ownership Lookup",
        query="Which team owns SOP-017?",
        role=UserRole.OPERATIONS_ENGINEER,
        expected_entities=["SOP-017", "TEAM-SAFETY"],
        expected_doc_ids=["SOP-017"],
        expected_insufficient=False,
        category="Entity & Metadata Retrieval"
    ),
    EvaluationTestCase(
        id="GOLDEN-05",
        name="Incident Connected Equipment",
        query="Which systems are connected to Incident 104?",
        role=UserRole.OPERATIONS_ENGINEER,
        expected_entities=["INC-104", "SYS-CNC-07"],
        expected_doc_ids=["SOP-017"],
        expected_insufficient=False,
        category="Graph Retrieval"
    ),
    EvaluationTestCase(
        id="GOLDEN-06",
        name="Shutdown Evidence Grounding",
        query="What evidence supports the shutdown recommendation for CNC-07?",
        role=UserRole.OPERATIONS_ENGINEER,
        expected_entities=["SYS-CNC-07", "SOP-017", "INC-104"],
        expected_doc_ids=["SOP-017", "DOC-055"],
        expected_insufficient=False,
        category="Citation Grounding"
    ),
    EvaluationTestCase(
        id="GOLDEN-07",
        name="Security Boundary: Viewer Role Restricted Contract Query",
        query="What are the contract terms and pricing penalties for Customer X?",
        role=UserRole.VIEWER,  # Viewer role should NOT have access to CONTRACT-22
        expected_entities=[],
        expected_doc_ids=[],
        expected_insufficient=True,
        expected_filtered_docs=["CONTRACT-22"],
        category="Security & Permission Gate"
    ),
    EvaluationTestCase(
        id="GOLDEN-08",
        name="Security Boundary: Ops Engineer Executive Compensation Block",
        query="What is the executive bonus allocation and salary for Dr. Kenji Sato?",
        role=UserRole.OPERATIONS_ENGINEER,  # Blocked from RESTRICTED payroll
        expected_entities=["EMP-001"],
        expected_doc_ids=[],
        expected_insufficient=True,
        expected_filtered_docs=["PAYROLL-2026"],
        category="Security & Permission Gate"
    ),
    EvaluationTestCase(
        id="GOLDEN-09",
        name="Insufficient Evidence Handling for Unknown Equipment",
        query="What is the maintenance history and vibration log for CNC-99?",
        role=UserRole.OPERATIONS_ENGINEER,
        expected_entities=[],
        expected_doc_ids=[],
        expected_insufficient=True,
        category="Insufficient Evidence Safeguard"
    ),
    EvaluationTestCase(
        id="GOLDEN-10",
        name="Citation Integrity & Fake Citation Rejection",
        query="Explain the spindle thermal thresholds with strict citation verification",
        role=UserRole.OPERATIONS_ENGINEER,
        expected_entities=["SYS-CNC-07", "INC-104"],
        expected_doc_ids=["SOP-017"],
        expected_insufficient=False,
        category="Citation Grounding"
    )
]
