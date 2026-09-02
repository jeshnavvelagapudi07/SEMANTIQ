"""
Graph Service
Handles Knowledge Graph representation, bounded multi-hop traversal, cycle safety, and path ranking.
Uses NetworkX with support for authorization-aware subgraphs.
"""
from typing import Optional
import networkx as nx
from app.models.schemas import (
    Entity,
    Relationship,
    UserRole,
    GraphPath,
    EntityType,
    RelationType
)
from app.services.permission_service import permission_service


class GraphService:
    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self.entities_by_id: dict[str, Entity] = {}
        self.relationships_by_id: dict[str, Relationship] = {}

    def load_data(self, entities: list[Entity], relationships: list[Relationship]):
        """Initializes the graph from seed entities and relationships."""
        self.graph.clear()
        self.entities_by_id.clear()
        self.relationships_by_id.clear()

        for entity in entities:
            self.entities_by_id[entity.id] = entity
            self.graph.add_node(
                entity.id,
                name=entity.name,
                type=entity.type.value,
                classification=entity.classification.value,
                description=entity.description,
                owner_team=entity.owner_team,
                properties=entity.properties
            )

        for rel in relationships:
            self.relationships_by_id[rel.id] = rel
            self.graph.add_edge(
                rel.source_id,
                rel.target_id,
                key=rel.id,
                id=rel.id,
                relation_type=rel.relation_type.value,
                description=rel.description,
                weight=rel.weight
            )

    def get_authorized_subgraph(self, role: UserRole) -> nx.MultiDiGraph:
        """
        Extracts a view of the graph containing ONLY authorized nodes.
        Edges connecting to unauthorized nodes are automatically pruned.
        """
        authorized_nodes = [
            node_id for node_id, entity in self.entities_by_id.items()
            if permission_service.is_authorized(role, entity.classification)
        ]
        return self.graph.subgraph(authorized_nodes).copy()

    def find_paths_between(
        self,
        source_id: str,
        target_id: str,
        role: UserRole,
        max_hops: int = 4
    ) -> list[GraphPath]:
        """
        Finds all simple paths between source_id and target_id up to max_hops
        in the authorized subgraph.
        """
        subgraph = self.get_authorized_subgraph(role)
        if source_id not in subgraph or target_id not in subgraph:
            return []

        # Convert to undirected view for bi-directional traversal search, then reconstruct directed edges
        undirected = subgraph.to_undirected(as_view=True)
        try:
            raw_paths = nx.all_simple_paths(undirected, source=source_id, target=target_id, cutoff=max_hops)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

        graph_paths: list[GraphPath] = []
        for path in raw_paths:
            rel_names: list[str] = []
            descriptions: list[str] = []
            score = 1.0 / (len(path) - 1 if len(path) > 1 else 1)

            for i in range(len(path) - 1):
                u, v = path[i], path[i+1]
                # Look for edge u->v or v->u in original subgraph
                edge_data = None
                if subgraph.has_edge(u, v):
                    edge_dict = subgraph.get_edge_data(u, v)
                    first_key = list(edge_dict.keys())[0]
                    edge_data = edge_dict[first_key]
                    rel_names.append(edge_data.get("relation_type", "RELATED_TO"))
                    descriptions.append(f"{self.entities_by_id[u].name} -> [{edge_data.get('relation_type')}] -> {self.entities_by_id[v].name}")
                elif subgraph.has_edge(v, u):
                    edge_dict = subgraph.get_edge_data(v, u)
                    first_key = list(edge_dict.keys())[0]
                    edge_data = edge_dict[first_key]
                    rel_names.append(f"INVERSE_{edge_data.get('relation_type', 'RELATED_TO')}")
                    descriptions.append(f"{self.entities_by_id[u].name} <- [{edge_data.get('relation_type')}] <- {self.entities_by_id[v].name}")
                else:
                    rel_names.append("CONNECTED_TO")
                    descriptions.append(f"{self.entities_by_id[u].name} <-> {self.entities_by_id[v].name}")

            graph_paths.append(GraphPath(
                path_nodes=path,
                path_relationships=rel_names,
                description=" | ".join(descriptions),
                length=len(path) - 1,
                score=score
            ))

        # Sort by shortest hop length first
        graph_paths.sort(key=lambda p: p.length)
        return graph_paths[:5]

    def traverse_for_entities(
        self,
        seed_entity_ids: list[str],
        role: UserRole,
        max_hops: int = 3
    ) -> list[GraphPath]:
        """
        Discovers paths connecting seed entities to each other and their immediate
        high-impact neighborhood (systems, incidents, SOPs, dependent projects).
        """
        subgraph = self.get_authorized_subgraph(role)
        valid_seeds = [s for s in seed_entity_ids if s in subgraph]
        if not valid_seeds:
            return []

        paths_found: list[GraphPath] = []
        seen_signatures = set()

        # Pairwise paths between seeds
        if len(valid_seeds) > 1:
            for i in range(len(valid_seeds)):
                for j in range(i + 1, len(valid_seeds)):
                    p_list = self.find_paths_between(valid_seeds[i], valid_seeds[j], role, max_hops=max_hops)
                    for p in p_list:
                        sig = "-".join(p.path_nodes)
                        if sig not in seen_signatures:
                            seen_signatures.add(sig)
                            paths_found.append(p)

        # Multi-hop neighborhood expansion for each seed
        for seed_id in valid_seeds:
            seed_entity = self.entities_by_id.get(seed_id)
            # Find neighbors up to 2 hops
            undirected = subgraph.to_undirected(as_view=True)
            try:
                lengths = nx.single_source_shortest_path_length(undirected, seed_id, cutoff=2)
            except nx.NodeNotFound:
                continue

            for target_id, dist in lengths.items():
                if target_id == seed_id or dist == 0:
                    continue
                # Focus on valuable target types: Projects, Incidents, Systems, Policies
                target_entity = self.entities_by_id.get(target_id)
                if target_entity and target_entity.type in {EntityType.PROJECT, EntityType.SYSTEM, EntityType.INCIDENT, EntityType.POLICY, EntityType.TEAM}:
                    p_list = self.find_paths_between(seed_id, target_id, role, max_hops=2)
                    for p in p_list:
                        sig = "-".join(p.path_nodes)
                        if sig not in seen_signatures:
                            seen_signatures.add(sig)
                            paths_found.append(p)

        # Sort by relevance score
        paths_found.sort(key=lambda p: (p.length, -p.score))
        return paths_found[:8]

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        return self.entities_by_id.get(entity_id)

    def get_all_entities(self, role: UserRole) -> list[Entity]:
        return [
            e for e in self.entities_by_id.values()
            if permission_service.is_authorized(role, e.classification)
        ]

    def get_all_relationships(self, role: UserRole) -> list[Relationship]:
        authorized_subgraph = self.get_authorized_subgraph(role)
        results = []
        for rel in self.relationships_by_id.values():
            if rel.source_id in authorized_subgraph and rel.target_id in authorized_subgraph:
                results.append(rel)
        return results

    def get_stats(self, role: UserRole) -> dict:
        subgraph = self.get_authorized_subgraph(role)
        type_counts = {}
        for node_id in subgraph.nodes():
            entity = self.entities_by_id.get(node_id)
            if entity:
                t = entity.type.value
                type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_nodes": subgraph.number_of_nodes(),
            "total_edges": subgraph.number_of_edges(),
            "entity_types": type_counts,
            "density": round(nx.density(subgraph), 4) if subgraph.number_of_nodes() > 1 else 0.0,
            "connected_components": nx.number_connected_components(subgraph.to_undirected(as_view=True)) if subgraph.number_of_nodes() > 0 else 0
        }


graph_service = GraphService()
