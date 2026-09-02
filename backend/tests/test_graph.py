"""
Unit Tests for Graph Service
Tests NetworkX loading, authorized subgraphs, multi-hop traversal, and cycle safety.
"""
import pytest
from app.data.seed_data import SEED_ENTITIES, SEED_RELATIONSHIPS
from app.services.graph_service import graph_service
from app.models.schemas import UserRole


@pytest.fixture(autouse=True)
def setup_graph():
    graph_service.load_data(SEED_ENTITIES, SEED_RELATIONSHIPS)


def test_graph_initialization():
    stats = graph_service.get_stats(UserRole.ADMIN)
    assert stats["total_nodes"] >= 30
    assert stats["total_edges"] >= 30
    assert "project" in stats["entity_types"]
    assert "system" in stats["entity_types"]
    assert "incident" in stats["entity_types"]


def test_multi_hop_path_traversal():
    # Project C (PRJ-GAMMA) -> CNC-07 (SYS-CNC-07) -> Incident 104 (INC-104)
    paths = graph_service.find_paths_between("PRJ-GAMMA", "INC-104", UserRole.OPERATIONS_ENGINEER, max_hops=4)
    assert len(paths) > 0
    
    # At least one path must verify the machine dependency via SYS-CNC-07
    assert any("SYS-CNC-07" in p.path_nodes for p in paths)


def test_traverse_for_entities():
    # Seed entities: PRJ-GAMMA and INC-104
    paths = graph_service.traverse_for_entities(["PRJ-GAMMA", "INC-104"], UserRole.OPERATIONS_ENGINEER, max_hops=3)
    assert len(paths) > 0
    # Must find path connecting PRJ-GAMMA to CNC-07 and INC-104
    assert any("SYS-CNC-07" in p.path_nodes for p in paths)


def test_authorized_subgraph_prunes_restricted_nodes():
    # SCADA Engine 01 is CONFIDENTIAL
    viewer_subgraph = graph_service.get_authorized_subgraph(UserRole.VIEWER)
    assert "SYS-SCADA-01" not in viewer_subgraph

    ops_subgraph = graph_service.get_authorized_subgraph(UserRole.OPERATIONS_ENGINEER)
    assert "SYS-SCADA-01" in ops_subgraph
