"""
Tests for Sequential Query State Isolation
Verifies that query N never leaves stale state or evidence in query N+1.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_sequential_query_state_isolation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Query Project Gamma (Project C)
        res1 = await client.post("/api/query", json={
            "query": "Why is Project C considered high risk?",
            "role": "operations_engineer"
        })
        assert res1.status_code == 200
        data1 = res1.json()
        assert "PRJ-GAMMA" in data1["reasoning_trace"]["authorized_entities"]
        assert any("DOC-031" in ev["doc_id"] for ev in data1["evidence"])

        # Step 2: Query Project Delta immediately after
        res2 = await client.post("/api/query", json={
            "query": "What is Project Delta and which system does it depend on?",
            "role": "operations_engineer"
        })
        assert res2.status_code == 200
        data2 = res2.json()
        assert "PRJ-DELTA" in data2["reasoning_trace"]["authorized_entities"]
        assert "PRJ-GAMMA" not in data2["reasoning_trace"]["authorized_entities"]
        # Must NOT contain Project Gamma evidence
        for ev in data2["evidence"]:
            assert "PRJ-GAMMA" not in ev["relevant_entities"]
            assert ev["doc_id"] != "DOC-031"
        assert "Project Gamma" not in data2["answer"]

        # Step 3: Query Project Zeta
        res3 = await client.post("/api/query", json={
            "query": "What is Project Zeta and which systems does it depend on?",
            "role": "operations_engineer"
        })
        assert res3.status_code == 200
        data3 = res3.json()
        assert "PRJ-ZETA" in data3["reasoning_trace"]["authorized_entities"]
        assert "PRJ-DELTA" not in data3["reasoning_trace"]["authorized_entities"]
        for ev in data3["evidence"]:
            assert "PRJ-DELTA" not in ev["relevant_entities"]
            assert "PRJ-GAMMA" not in ev["relevant_entities"]

        # Step 4: Query Incident 104
        res4 = await client.post("/api/query", json={
            "query": "Which projects are affected by Incident 104 and what should the responsible team do?",
            "role": "operations_engineer"
        })
        assert res4.status_code == 200
        data4 = res4.json()
        assert "INC-104" in data4["reasoning_trace"]["authorized_entities"]

        # Step 5: Query Project Delta again
        res5 = await client.post("/api/query", json={
            "query": "What is Project Delta and which system does it depend on?",
            "role": "operations_engineer"
        })
        assert res5.status_code == 200
        data5 = res5.json()
        assert "PRJ-DELTA" in data5["reasoning_trace"]["authorized_entities"]
        assert "INC-104" not in data5["reasoning_trace"]["authorized_entities"]
        for ev in data5["evidence"]:
            assert "INC-104" not in ev["relevant_entities"]
