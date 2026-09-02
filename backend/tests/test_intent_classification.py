"""
Tests for Intent Classification Service
"""
import pytest
from app.models.schemas import QueryIntent
from app.services.intent_service import intent_service


def test_restricted_query_intent():
    intent, _ = intent_service.classify_intent("Show me the Aerospace Prime Master Supply Agreement for Customer X and summarize its commercial terms.")
    assert intent == QueryIntent.RESTRICTED_QUERY

    intent, _ = intent_service.classify_intent("What are the executive salaries and payroll bonuses in PAYROLL-2026?")
    assert intent == QueryIntent.RESTRICTED_QUERY


def test_evidence_query_intent():
    intent, _ = intent_service.classify_intent("What evidence proves that Project Delta depends on SYS-FURN-05?")
    assert intent == QueryIntent.EVIDENCE_QUERY

    intent, _ = intent_service.classify_intent("Show me documentary evidence for CNC-07 bearing overhaul.")
    assert intent == QueryIntent.EVIDENCE_QUERY


def test_impact_and_incident_intent():
    intent, _ = intent_service.classify_intent("Which projects are affected by Incident 104 and what should the responsible team do?")
    assert intent in [QueryIntent.IMPACT_QUERY, QueryIntent.POLICY_QUERY]

    intent, _ = intent_service.classify_intent("What happened in Incident 104?")
    assert intent == QueryIntent.INCIDENT_QUERY


def test_dependency_query_intent():
    intent, _ = intent_service.classify_intent("What is CNC-07 and what projects depend on it?")
    assert intent == QueryIntent.DEPENDENCY_QUERY

    intent, _ = intent_service.classify_intent("What is Project Delta and which system does it depend on?")
    assert intent == QueryIntent.DEPENDENCY_QUERY


def test_ownership_intent():
    intent, _ = intent_service.classify_intent("Which team owns SOP-017 and what is the escalation procedure?")
    assert intent in [QueryIntent.OWNERSHIP_QUERY, QueryIntent.POLICY_QUERY]
