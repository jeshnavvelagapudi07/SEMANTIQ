"""
Unit & Integration Tests for PostgreSQL Database Backend and Adapter Layer
Validates PostgreSQL engine selection, schema isolation, query translation,
DbRow universal mapping, table creation, user CRUD, auth lookup, entity/relationship
lifecycle, audit logging, transactions, and seed idempotency without requiring an external DB.
"""
import pytest
from unittest.mock import MagicMock, patch
from app.core.config import Settings
from app.core.database import (
    _translate_placeholders,
    DbRow,
    PostgresCursorWrapper,
    PostgresConnectionWrapper,
    hash_password,
    verify_password
)


def test_database_url_validation_rejects_sqlite(monkeypatch):
    """Verifies that a SQLite DATABASE_URL raises RuntimeError at config construction."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./semantiq.db")
    with pytest.raises(RuntimeError, match="SQLite"):
        Settings()


def test_database_url_validation_rejects_missing(monkeypatch):
    """Verifies that a missing DATABASE_URL raises RuntimeError at config construction."""
    monkeypatch.setenv("DATABASE_URL", "")
    with pytest.raises(RuntimeError, match="DATABASE_URL is not set"):
        Settings()


def test_database_url_validation_accepts_postgresql(monkeypatch):
    """Verifies that a postgresql:// URL passes config construction."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
    s = Settings()
    assert "postgresql" in s.DATABASE_URL


def test_sql_placeholder_translation():
    """Verifies SQL translation converts ? to %s placeholders for psycopg."""
    q1 = "SELECT id, email, role FROM users WHERE id = ? AND status = ?"
    t1 = _translate_placeholders(q1)
    assert t1 == "SELECT id, email, role FROM users WHERE id = %s AND status = %s"

    q2 = "SELECT * FROM users WHERE LOWER(email) = LOWER(?) OR LOWER(username) = LOWER(?)"
    t2 = _translate_placeholders(q2)
    assert t2 == "SELECT * FROM users WHERE LOWER(email) = LOWER(%s) OR LOWER(username) = LOWER(%s)"

    # No ? — should pass through unchanged
    q3 = "SELECT COUNT(*) FROM users WHERE role = %s"
    assert _translate_placeholders(q3) == q3


def test_db_row_mapping_and_indexing():
    """Verifies DbRow provides dictionary conversion, case-insensitive access, and integer indexing."""
    cols = ["id", "display_name", "role", "clearance_level"]
    vals = ["usr_001", "Kenji Sato", "operations_engineer", "CONFIDENTIAL"]
    row = DbRow(cols, vals)

    assert row["id"] == "usr_001"
    assert row["display_name"] == "Kenji Sato"
    assert row["role"] == "operations_engineer"
    assert row["ROLE"] == "operations_engineer"
    assert row["Clearance_Level"] == "CONFIDENTIAL"
    assert row[0] == "usr_001"
    assert row[1] == "Kenji Sato"

    d = dict(row)
    assert isinstance(d, dict)
    assert d["id"] == "usr_001"

    assert "id" in row
    assert "ROLE" in row
    assert len(row) == 4
    assert list(row.keys()) == cols


def test_postgres_schema_isolation_on_connect():
    """Verifies that every PostgreSQL connection enforces dedicated schema isolation ('semantiq')."""
    mock_raw_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_raw_conn.cursor.return_value.__enter__.return_value = mock_cursor

    wrapper = PostgresConnectionWrapper(mock_raw_conn)

    executed_statements = [call[0][0] for call in mock_cursor.execute.call_args_list]
    assert any("CREATE SCHEMA IF NOT EXISTS semantiq" in stmt for stmt in executed_statements)
    assert any("SET search_path TO semantiq, public" in stmt for stmt in executed_statements)
    assert mock_raw_conn.commit.called


def test_postgres_adapter_crud_lifecycle():
    """Verifies complete query execution, user insert, auth lookup, and audit trail under Postgres wrapper."""
    mock_raw_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_raw_conn.cursor.return_value = mock_cursor

    wrapper = PostgresConnectionWrapper(mock_raw_conn)

    p_hash, salt = hash_password("SecurePassword2026!")
    user_data = ("usr_test_01", "EMP-999", "test_user", "test@semantiq.org", p_hash, salt, "Test User", "operations_engineer")
    cur = wrapper.cursor()
    cur.execute("""
        INSERT INTO users (id, employee_id, username, email, password_hash, salt, display_name, role)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (id) DO NOTHING
    """, user_data)

    last_query, last_params = mock_cursor.execute.call_args[0]
    assert "%s, %s, %s, %s, %s, %s, %s, %s" in last_query
    assert last_params == user_data

    desc = [MagicMock(name="id"), MagicMock(name="password_hash"), MagicMock(name="salt"), MagicMock(name="status")]
    desc[0].name = "id"
    desc[1].name = "password_hash"
    desc[2].name = "salt"
    desc[3].name = "status"
    mock_cursor.description = desc
    mock_cursor.fetchone.return_value = ("usr_test_01", p_hash, salt, "ACTIVE")

    cur.execute("SELECT id, password_hash, salt, status FROM users WHERE email = ?", ("test@semantiq.org",))
    found_row = cur.fetchone()

    assert found_row is not None
    assert found_row["id"] == "usr_test_01"
    assert found_row["status"] == "ACTIVE"
    assert verify_password("SecurePassword2026!", found_row["password_hash"], found_row["salt"]) is True

    wrapper.commit()
    assert mock_raw_conn.commit.called

    wrapper.close()
    assert mock_raw_conn.close.called


def test_postgres_transaction_context_manager_rollback_on_exception():
    """Verifies that PostgreSQL connection context manager executes rollback on error."""
    mock_raw_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_raw_conn.cursor.return_value.__enter__.return_value = mock_cursor

    wrapper = PostgresConnectionWrapper(mock_raw_conn)

    with pytest.raises(ValueError, match="Simulated database write error"):
        with wrapper as conn:
            conn.execute("INSERT INTO users VALUES (%s)", ("invalid_data",))
            raise ValueError("Simulated database write error")

    assert mock_raw_conn.rollback.called
    assert mock_raw_conn.close.called


def test_postgres_seed_idempotency():
    """Verifies that seed operations use ON CONFLICT (id) DO NOTHING so repeated runs do not fail."""
    from app.data.seed_data import SEED_ENTITIES, SEED_RELATIONSHIPS
    from app.core.database import _seed_initial_graph

    mock_raw_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_raw_conn.cursor.return_value = mock_cursor
    mock_raw_conn.cursor.return_value.__enter__.return_value = mock_cursor

    wrapper = PostgresConnectionWrapper(mock_raw_conn)
    _seed_initial_graph(wrapper)

    executed_statements = [call[0][0] for call in mock_cursor.execute.call_args_list]
    insert_stmts = [s for s in executed_statements if "INSERT" in s]
    assert len(insert_stmts) == len(SEED_ENTITIES) + len(SEED_RELATIONSHIPS)
    assert all("ON CONFLICT (id) DO NOTHING" in stmt for stmt in insert_stmts)


def test_audit_log_upsert_postgres_compatible():
    """
    Regression test: verifies the audit_logs INSERT...ON CONFLICT upsert is PostgreSQL-compatible.
    Guards against the production bug where 'INSERT OR REPLACE INTO audit_logs'
    caused psycopg.errors.SyntaxError on Render.
    """
    import json
    from app.services.audit_service import AuditService

    audit_upsert_sql = """
                INSERT INTO audit_logs (
                    id, timestamp, user_id, user_role, query,
                    identified_entities, authorized_entities, filtered_entities_count, filtered_details,
                    graph_paths_count, evidence_ids, llm_provider, validation_status,
                    confidence_score, confidence_level, recommendation, requires_human_review,
                    action_id, action_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    timestamp = EXCLUDED.timestamp,
                    user_id = EXCLUDED.user_id,
                    user_role = EXCLUDED.user_role,
                    query = EXCLUDED.query,
                    identified_entities = EXCLUDED.identified_entities,
                    authorized_entities = EXCLUDED.authorized_entities,
                    filtered_entities_count = EXCLUDED.filtered_entities_count,
                    filtered_details = EXCLUDED.filtered_details,
                    graph_paths_count = EXCLUDED.graph_paths_count,
                    evidence_ids = EXCLUDED.evidence_ids,
                    llm_provider = EXCLUDED.llm_provider,
                    validation_status = EXCLUDED.validation_status,
                    confidence_score = EXCLUDED.confidence_score,
                    confidence_level = EXCLUDED.confidence_level,
                    recommendation = EXCLUDED.recommendation,
                    requires_human_review = EXCLUDED.requires_human_review,
                    action_id = EXCLUDED.action_id,
                    action_status = EXCLUDED.action_status
            """

    assert "INSERT OR REPLACE" not in audit_upsert_sql.upper()
    assert "ON CONFLICT (id) DO UPDATE SET" in audit_upsert_sql

    translated = _translate_placeholders(audit_upsert_sql)
    assert "?" not in translated
    assert "%s" in translated

    mock_raw_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_raw_conn.cursor.return_value = mock_cursor

    wrapper = PostgresConnectionWrapper(mock_raw_conn)

    params = (
        "QRY-test-001", "2026-09-03T12:00:00Z", "usr_ops_01",
        "operations_engineer", "What failed on CNC-07?",
        json.dumps(["SYS-CNC-07"]), json.dumps(["SYS-CNC-07"]),
        0, json.dumps([]), 2, json.dumps(["EVID-001"]),
        "gemini", "VALIDATED", 0.87, "HIGH",
        "Inspect spindle bearing.", 0, "", "",
    )

    cur = wrapper.cursor()
    cur.execute(audit_upsert_sql, params)
    updated_params = params[:1] + ("2026-09-03T13:00:00Z",) + params[2:]
    cur.execute(audit_upsert_sql, updated_params)

    assert mock_cursor.execute.call_count == 2
    for actual_call in mock_cursor.execute.call_args_list:
        executed_sql = actual_call[0][0]
        assert "INSERT OR REPLACE" not in executed_sql.upper()
        assert "%s" in executed_sql
        assert "ON CONFLICT (id) DO UPDATE SET" in executed_sql

    import inspect
    source = inspect.getsource(AuditService.log_query)
    assert "INSERT OR REPLACE" not in source.upper()
    assert "ON CONFLICT (id) DO UPDATE SET" in source


def test_seed_benchmark_users_are_idempotent_by_email():
    """
    Verifies that _seed_benchmark_users_if_absent skips INSERT when the SELECT check
    confirms users already exist (fetchone returns a row, not None).

    Uses a fully spec'd mock that makes PostgresCursorWrapper.fetchone() return a
    valid DbRow (simulating an existing user record) for every call.
    """
    from app.core.database import _seed_benchmark_users_if_absent

    mock_raw_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_raw_conn.cursor.return_value = mock_cursor
    mock_raw_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Give the mock cursor a valid description so PostgresCursorWrapper.fetchone() works
    desc_col = MagicMock()
    desc_col.name = "id"
    mock_cursor.description = [desc_col]

    # fetchone() returns a real tuple row (not None) → PostgresCursorWrapper builds a DbRow
    mock_cursor.fetchone.return_value = ("usr_existing_01",)

    wrapper = PostgresConnectionWrapper(mock_raw_conn)
    _seed_benchmark_users_if_absent(wrapper)

    # No INSERT INTO users should have been executed since fetchone found an existing row
    insert_calls = [
        call for call in mock_cursor.execute.call_args_list
        if call[0] and "INSERT INTO users" in str(call[0][0])
    ]
    assert len(insert_calls) == 0, (
        "Seeding must NOT INSERT when users already exist — existing passwords must not be overwritten."
    )

    # 4 SELECT checks must have been issued (one per benchmark user)
    select_calls = [
        call for call in mock_cursor.execute.call_args_list
        if call[0] and "SELECT" in str(call[0][0]).upper() and "email" in str(call[0][0]).lower()
    ]
    assert len(select_calls) == 4, (
        f"Expected 4 SELECT checks (one per benchmark user), got {len(select_calls)}."
    )


def test_password_hashing_never_stores_plaintext():
    """Verifies PBKDF2-HMAC-SHA256 hashing always returns hash != plaintext."""
    for pwd in ["Test1234!", "SomeComplexPassword!2026", "short", "a" * 100]:
        h, s = hash_password(pwd)
        assert h != pwd
        assert len(h) == 64  # 32-byte hex
        assert len(s) == 32  # 16-byte hex
        assert verify_password(pwd, h, s) is True
        assert verify_password(pwd + "x", h, s) is False
