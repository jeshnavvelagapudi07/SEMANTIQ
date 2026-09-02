from typing import Optional
from fastapi import APIRouter, Query, Depends
from app.models.schemas import UserRole, Entity, Relationship
from app.core.auth import get_current_user, resolve_effective_role, AuthUser
from app.services.graph_service import graph_service

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])


@router.get("")
def get_graph(
    role: Optional[UserRole] = Query(None),
    current_user: Optional[AuthUser] = Depends(get_current_user)
):
    """
    Returns the full knowledge graph (nodes + edges) authorized for the role.
    """
    effective_role, _ = resolve_effective_role(current_user, client_supplied_role=role)
    entities = graph_service.get_all_entities(effective_role)
    relationships = graph_service.get_all_relationships(effective_role)
    stats = graph_service.get_stats(effective_role)

    # Format nodes for React Flow / Graph visualizer
    nodes = [
        {
            "id": e.id,
            "name": e.name,
            "type": e.type.value,
            "classification": e.classification.value,
            "description": e.description,
            "owner_team": e.owner_team,
            "properties": e.properties
        }
        for e in entities
    ]

    edges = [
        {
            "id": r.id,
            "source": r.source_id,
            "target": r.target_id,
            "relation_type": r.relation_type.value,
            "description": r.description,
            "weight": r.weight
        }
        for r in relationships
    ]

    return {
        "role": effective_role.value,
        "nodes": nodes,
        "edges": edges,
        "stats": stats
    }


@router.get("/{entity_id}")
def get_entity_subgraph(
    entity_id: str,
    role: Optional[UserRole] = Query(None),
    hops: int = Query(2, ge=1, le=4),
    current_user: Optional[AuthUser] = Depends(get_current_user)
):
    effective_role, _ = resolve_effective_role(current_user, client_supplied_role=role)
    """
    Returns the k-hop neighborhood graph centered around an entity.
    """
    subgraph = graph_service.get_authorized_subgraph(effective_role)
    if entity_id not in subgraph:
        return {"nodes": [], "edges": [], "entity_id": entity_id, "found": False}

    import networkx as nx
    undirected = subgraph.to_undirected(as_view=True)
    lengths = nx.single_source_shortest_path_length(undirected, entity_id, cutoff=hops)
    node_ids = set(lengths.keys())

    nodes = [
        {
            "id": e.id,
            "name": e.name,
            "type": e.type.value,
            "classification": e.classification.value,
            "description": e.description,
            "owner_team": e.owner_team,
            "properties": e.properties
        }
        for nid in node_ids
        if (e := graph_service.get_entity(nid)) is not None
    ]

    edges = []
    for rel in graph_service.get_all_relationships(effective_role):
        if rel.source_id in node_ids and rel.target_id in node_ids:
            edges.append({
                "id": rel.id,
                "source": rel.source_id,
                "target": rel.target_id,
                "relation_type": rel.relation_type.value,
                "description": rel.description,
                "weight": rel.weight
            })

    return {
        "center_entity_id": entity_id,
        "hops": hops,
        "nodes": nodes,
        "edges": edges,
        "found": True
    }
