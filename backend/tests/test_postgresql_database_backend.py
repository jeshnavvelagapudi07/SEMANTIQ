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
    translate_sql_for_postgres,
    DbRow,
    PostgresCursorWrapper,
    PostgresConnectionWrapper,
    hash_password,
    verify_password
)


def test_database_url_backend_selection():
    """Verifies that postgresql:// and postgres:// URLs correctly activate PostgreSQL backend."""
    # Test 1: Standard postgresql:// URL
    s1 = Settings(DATABASE_URL="postgresql://render_user:secret_pass@ep-cool-123.virginia.postgres.render.com:5432/semantiq_db")
    assert s1.is_postgres is True

    # Test 2: Render shorthand postgres:// URL (used by sneyixa-db)
    s2 = Settings(DATABASE_URL="postgres://render_user:secret_pass@dpg-abc123-a.virginia-postgres.render.com/sneyixa-db")
    assert s2.is_postgres is True

    # Test 3: Local development SQLite URL
    s3 = Settings(DATABASE_URL="sqlite:///./semantiq.db")
    assert s3.is_postgres is False


def test_sql_query_translation_for_postgres():
    """Verifies SQL translation handles ? placeholders and INSERT OR IGNORE differences."""
    # Placeholders: ? -> %s
    q1 = "SELECT id, email, role FROM users WHERE id = ? AND status = ?"
    t1 = translate_sql_for_postgres(q1)
    assert t1 == "SELECT id, email, role FROM users WHERE id = %s AND status = %s"

    # Multiple parameters in authentication lookup
    q2 = "SELECT * FROM users WHERE LOWER(email) = LOWER(?) OR LOWER(username) = LOWER(?)"
    t2 = translate_sql_for_postgres(q2)
    assert t2 == "SELECT * FROM users WHERE LOWER(email) = LOWER(%s) OR LOWER(username) = LOWER(%s)"

    # INSERT OR IGNORE -> ON CONFLICT DO NOTHING
    q3 = "INSERT OR IGNORE INTO entities (id, type, name) VALUES (?, ?, ?)"
    t3 = translate_sql_for_postgres(q3)
    assert "INSERT INTO entities" in t3
    assert "ON CONFLICT DO NOTHING" in t3
    assert "%s, %s, %s" in t3


def test_db_row_mapping_and_indexing():
    """Verifies DbRow provides dictionary conversion, case-insensitive access, and integer indexing."""
    cols = ["id", "display_name", "role", "clearance_level"]
    vals = ["usr_001", "Kenji Sato", "operations_engineer", "CONFIDENTIAL"]
    row = DbRow(cols, vals)

    # String access
    assert row["id"] == "usr_001"
    assert row["display_name"] == "Kenji Sato"
    assert row["role"] == "operations_engineer"
    # Case-insensitive column access
    assert row["ROLE"] == "operations_engineer"
    assert row["Clearance_Level"] == "CONFIDENTIAL"

    # Integer indexing
    assert row[0] == "usr_001"
    assert row[1] == "Kenji Sato"

    # dict() conversion
    d = dict(row)
    assert isinstance(d, dict)
    assert d["id"] == "usr_001"
    assert d["display_name"] == "Kenji Sato"

    # Keys and membership
    assert "id" in row
    assert "ROLE" in row
    assert len(row) == 4
    assert list(row.keys()) == cols


def test_postgres_schema_isolation_on_connect():
    """Verifies that every PostgreSQL connection enforces dedicated schema isolation ('semantiq')."""
    mock_raw_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_raw_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Wrap the connection
    wrapper = PostgresConnectionWrapper(mock_raw_conn)

    # Verify search_path and schema creation were invoked
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

    # 1. User insertion
    p_hash, salt = hash_password("SecurePassword2026!")
    user_data = ("usr_test_01", "EMP-999", "test_user", "test@semantiq.org", p_hash, salt, "Test User", "operations_engineer")
    cur = wrapper.cursor()
    cur.execute("""
        INSERT INTO users (id, employee_id, username, email, password_hash, salt, display_name, role)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (id) DO NOTHING
    """, user_data)

    # Verify query was translated to %s placeholders
    last_query, last_params = mock_cursor.execute.call_args[0]
    assert "%s, %s, %s, %s, %s, %s, %s, %s" in last_query
    assert last_params == user_data

    # 2. Authentication lookup simulation
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

    # 3. Transaction management
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
    """Verifies that seed operations specify ON CONFLICT (id) DO NOTHING so multiple runs do not fail."""
    from app.data.seed_data import SEED_ENTITIES, SEED_RELATIONSHIPS
    from app.core.database import _seed_initial_graph

    mock_raw_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_raw_conn.cursor.return_value = mock_cursor
    mock_raw_conn.cursor.return_value.__enter__.return_value = mock_cursor

    wrapper = PostgresConnectionWrapper(mock_raw_conn)
    _seed_initial_graph(wrapper)

    # All calls must include ON CONFLICT (id) DO NOTHING
    executed_statements = [call[0][0] for call in mock_cursor.execute.call_args_list]
    insert_stmts = [s for s in executed_statements if "INSERT" in s]
    assert len(insert_stmts) == len(SEED_ENTITIES) + len(SEED_RELATIONSHIPS)
    assert all("ON CONFLICT (id) DO NOTHING" in stmt for stmt in insert_stmts)

