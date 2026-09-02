"""
Hybrid Retrieval Service
Combines Deterministic Entity Extraction, Scoped Graph Proximity Filtering,
Intent-Weighted Multidimensional Scoring, and Lexical TF-IDF Matching.
Enforces pre-LLM permission filtering and strict context minimization.
"""
import re
from typing import Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models.schemas import (
    Entity,
    Document,
    EvidenceChunk,
    UserRole,
    ClassificationLevel,
    FilteredItemSummary,
    GraphPath,
    QueryIntent
)
from app.services.permission_service import permission_service
from app.data.seed_data import SEED_ENTITIES, SEED_DOCUMENTS, SEED_EVIDENCE_CHUNKS


class RetrievalService:
    def __init__(self):
        self.entities: list[Entity] = list(SEED_ENTITIES)
        self.documents: list[Document] = list(SEED_DOCUMENTS)
        self.evidence_chunks: list[EvidenceChunk] = list(SEED_EVIDENCE_CHUNKS)
        
        # Build lookup tables
        self.entity_lookup: dict[str, Entity] = {e.id: e for e in self.entities}
        self.doc_lookup: dict[str, Document] = {d.id: d for d in self.documents}
        self.evidence_lookup: dict[str, EvidenceChunk] = {ev.id: ev for ev in self.evidence_chunks}
        
        # Precompute TF-IDF matrix over evidence chunks
        self._init_tfidf()

    def _init_tfidf(self):
        self.corpus = [
            f"{ev.doc_title} {ev.excerpt} {' '.join(ev.relevant_entities)} {' '.join(ev.supported_relationships)}"
            for ev in self.evidence_chunks
        ]
        self.vectorizer = TfidfVectorizer(stop_words='english', token_pattern=r'(?u)\b[\w-]+\b')
        if self.corpus:
            self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)
        else:
            self.tfidf_matrix = None

    def identify_entities(
        self,
        query: str,
        role: UserRole
    ) -> tuple[list[Entity], list[FilteredItemSummary]]:
        """
        Deterministically extracts entities from the query using IDs, names, and aliases,
        then evaluates role clearance.
        """
        matched_raw_entities: list[Entity] = []
        seen_ids = set()

        q_lower = query.lower()
        
        # Entity matching patterns & aliases
        alias_map = {
            "incident 104": "INC-104",
            "inc-104": "INC-104",
            "incident-104": "INC-104",
            "inc 104": "INC-104",
            "project c": "PRJ-GAMMA",
            "project gamma": "PRJ-GAMMA",
            "prj-gamma": "PRJ-GAMMA",
            "project alpha": "PRJ-ALPHA",
            "prj-alpha": "PRJ-ALPHA",
            "project beta": "PRJ-BETA",
            "prj-beta": "PRJ-BETA",
            "project delta": "PRJ-DELTA",
            "prj-delta": "PRJ-DELTA",
            "project epsilon": "PRJ-EPSILON",
            "prj-epsilon": "PRJ-EPSILON",
            "project zeta": "PRJ-ZETA",
            "prj-zeta": "PRJ-ZETA",
            "project eta": "PRJ-ETA",
            "prj-eta": "PRJ-ETA",
            "project theta": "PRJ-THETA",
            "prj-theta": "PRJ-THETA",
            "cnc-07": "SYS-CNC-07",
            "cnc 07": "SYS-CNC-07",
            "sys-cnc-07": "SYS-CNC-07",
            "cnc-04": "SYS-CNC-04",
            "chiller 02": "SYS-COOL-02",
            "plc-88": "SYS-PLC-88",
            "furnace 05": "SYS-FURN-05",
            "sys-furn-05": "SYS-FURN-05",
            "scanner 09": "SYS-OPT-09",
            "sys-opt-09": "SYS-OPT-09",
            "arm 02": "SYS-ARM-02",
            "sys-arm-02": "SYS-ARM-02",
            "hepa 04": "SYS-AIR-04",
            "sys-air-04": "SYS-AIR-04",
            "spindle thermal": "SYS-CNC-07",
            "thermal thresholds": "SOP-017",
            "sop-017": "SOP-017",
            "sop 017": "SOP-017",
            "doc-023": "DOC-023",
            "doc-031": "DOC-031",
            "doc-041": "DOC-041",
            "doc-055": "DOC-055",
            "doc-062": "DOC-062",
            "contract 22": "CONTRACT-22",
            "contract-22": "CONTRACT-22",
            "customer x": "CONTRACT-22",
            "payroll": "PAYROLL-2026",
            "salary": "PAYROLL-2026",
            "bonus": "PAYROLL-2026",
            "compensation": "PAYROLL-2026",
            "kenji sato": "EMP-001",
            "elena rostova": "EMP-002",
            "marcus vance": "EMP-003",
            "aoi tanaka": "EMP-004",
            "takeshi yamamoto": "EMP-005",
            "sarah jenkins": "EMP-006",
            "manufacturing operations": "TEAM-MFG-OPS",
            "reliability": "TEAM-RELIABILITY",
            "safety team": "TEAM-SAFETY",
            "quality assurance": "TEAM-QUALITY",
            "global aerospace dynamics": "CUST-AERO-GLOBAL"
        }

        # Check aliases
        for phrase, ent_id in alias_map.items():
            if phrase in q_lower:
                if ent_id in self.entity_lookup and ent_id not in seen_ids:
                    seen_ids.add(ent_id)
                    matched_raw_entities.append(self.entity_lookup[ent_id])
                elif ent_id in self.doc_lookup and ent_id not in seen_ids:
                    doc = self.doc_lookup[ent_id]
                    seen_ids.add(ent_id)
                    if permission_service.is_authorized(role, doc.classification):
                        for linked_id in doc.entity_ids:
                            if linked_id in self.entity_lookup and linked_id not in seen_ids:
                                seen_ids.add(linked_id)
                                matched_raw_entities.append(self.entity_lookup[linked_id])

        # Check all entity IDs and names directly
        for entity in self.entities:
            if entity.id in seen_ids:
                continue
            id_match = re.search(r'\b' + re.escape(entity.id.lower()) + r'\b', q_lower)
            name_match = re.search(r'\b' + re.escape(entity.name.lower()) + r'\b', q_lower)
            if id_match or name_match:
                seen_ids.add(entity.id)
                matched_raw_entities.append(entity)

        # Apply strict permission filter on identified entities
        authorized_entities, filtered_summaries = permission_service.filter_entities(role, matched_raw_entities)
        return authorized_entities, filtered_summaries

    def retrieve_evidence(
        self,
        query: str,
        role: UserRole,
        traversed_paths: list[GraphPath],
        authorized_entities: list[Entity],
        intent: QueryIntent = QueryIntent.GENERAL_KNOWLEDGE_QUERY,
        top_k: int = 5
    ) -> tuple[list[EvidenceChunk], list[FilteredItemSummary]]:
        """
        Scoped hybrid retrieval: Strictly scopes candidates to active query entities/paths,
        weights by query intent and relationship alignment, and applies TF-IDF matching.
        Guarantees zero cross-entity contamination.
        """
        # Step 1: Pre-filter evidence based on user role clearance
        authorized_chunks, filtered_summaries = permission_service.filter_evidence(role, self.evidence_chunks)
        if not authorized_chunks:
            return [], filtered_summaries

        # Build set of active query node IDs
        query_entity_ids = {e.id for e in authorized_entities}
        active_node_ids = set(query_entity_ids)
        for p in traversed_paths:
            active_node_ids.update(p.path_nodes)

        # Build pair relationships present in traversed paths
        active_pair_relationships = set()
        for p in traversed_paths:
            for i in range(len(p.path_nodes) - 1):
                src = p.path_nodes[i]
                tgt = p.path_nodes[i + 1]
                rel = p.path_relationships[i] if i < len(p.path_relationships) else "RELATED_TO"
                active_pair_relationships.add(f"{src}:{rel}:{tgt}")
                active_pair_relationships.add(f"{tgt}:{rel}:{src}")

        query_vec = self.vectorizer.transform([query])
        scored_chunks: list[tuple[float, EvidenceChunk]] = []

        for chunk in authorized_chunks:
            chunk_entities = set(chunk.relevant_entities)

            # Strict Entity-Scoping Gate:
            # If the user queried specific entities, the chunk MUST overlap with either
            # the direct query entities or direct active path nodes.
            overlap_query = chunk_entities.intersection(query_entity_ids)
            overlap_active = chunk_entities.intersection(active_node_ids)

            if active_node_ids and not overlap_active:
                # Chunk belongs to an unrelated entity -> Strictly Exclude
                continue

            # Project Isolation Rule:
            # If the query is specifically focused on a Project (query_projects non-empty),
            # do NOT retrieve chunks belonging to a different project unless that project is also in query_entity_ids.
            query_projects = {eid for eid in query_entity_ids if eid.startswith("PRJ-")}
            chunk_projects = {eid for eid in chunk_entities if eid.startswith("PRJ-")}
            if query_projects and chunk_projects and not chunk_projects.intersection(query_projects):
                continue

            # Dimension 1: Direct Entity Match (0.0 to 0.40)
            entity_score = 0.40 if overlap_query else (0.20 if overlap_active else 0.0)

            # Dimension 2: Explicit Relationship Match (0.0 to 0.30)
            rel_score = 0.0
            for supported_rel in chunk.supported_relationships:
                if supported_rel in active_pair_relationships:
                    rel_score = 0.30
                    break
                # Check if both endpoints of supported relationship are in active_node_ids
                parts = supported_rel.split(":")
                if len(parts) == 3 and parts[0] in active_node_ids and parts[2] in active_node_ids:
                    rel_score = 0.25
                    break

            # Dimension 3: Query Intent Match (0.0 to 0.20)
            intent_score = 0.0
            if intent in [QueryIntent.DEPENDENCY_QUERY, QueryIntent.ENTITY_DESCRIPTION]:
                if chunk.doc_type in ["Specification", "Maintenance Log"]:
                    intent_score = 0.20
            elif intent in [QueryIntent.POLICY_QUERY, QueryIntent.IMPACT_QUERY, QueryIntent.INCIDENT_QUERY]:
                if chunk.doc_type in ["SOP", "Policy Document", "Policy"]:
                    intent_score = 0.20
            elif intent == QueryIntent.EVIDENCE_QUERY:
                intent_score = 0.20 if rel_score > 0 else 0.10

            # Dimension 4: Lexical TF-IDF score (0.0 to 0.10)
            chunk_text = f"{chunk.doc_title} {chunk.excerpt} {' '.join(chunk.relevant_entities)}"
            chunk_vec = self.vectorizer.transform([chunk_text])
            lexical_sim = float(cosine_similarity(query_vec, chunk_vec)[0][0])
            tfidf_score = 0.10 * lexical_sim

            total_score = entity_score + rel_score + intent_score + tfidf_score

            # Only retain if there is genuine entity or topical grounding
            if total_score >= 0.20:
                scored_chunk = chunk.model_copy(update={"relevance_score": round(total_score, 3)})
                scored_chunks.append((total_score, scored_chunk))

        # Sort descending by composite score
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        if active_node_ids:
            top_evidence = [chunk for score, chunk in scored_chunks[:top_k] if score >= 0.20]
        else:
            top_evidence = []

        return top_evidence, filtered_summaries

    def get_document(self, doc_id: str) -> Optional[Document]:
        return self.doc_lookup.get(doc_id)

    def get_evidence_chunk(self, evidence_id: str) -> Optional[EvidenceChunk]:
        return self.evidence_lookup.get(evidence_id)


retrieval_service = RetrievalService()
