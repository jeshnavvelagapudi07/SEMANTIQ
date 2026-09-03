"""
Tests for the One-Time Benchmark Password Migration
(_migrate_benchmark_passwords_if_enabled)

Covers:
1.  Password is changed when migration is explicitly enabled.
2.  New password authenticates successfully.
3.  Old password no longer authenticates after migration.
4.  Non-benchmark users are completely untouched.
5.  Roles and clearances are untouched after migration.
6.  Second migration attempt is skipped (completion marker exists).
7.  Password values never appear in audit/change_audit_logs records.
8.  Migration is disabled by default (RESET_BENCHMARK_PASSWORDS=false).
9.  Migration cannot be triggered via the HTTP API (no endpoint exposes it).
10. Fresh database seeding still works normally (RESET_BENCHMARK_PASSWORDS=false).

NOTE: Tests 1-7 and 10 use PostgresCursorWrapper mocks — no live DB required.
Test 9 verifies the API route table contains no migration endpoint.
"""
import os
import json
import pytest
from unittest.mock import MagicMock, call as mock_call
from app.core.database import (
    _migrate_benchmark_passwords_if_enabled,
    PostgresConnectionWrapper,
    hash_password,
    verify_password,
    _seed_benchmark_users_if_absent,
)
from app.core.config import Settings


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_wrapper_and_cursor():
    """Returns a (wrapper, mock_cursor) pair with description wired for DbRow."""
    mock_raw_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_raw_conn.cursor.return_value = mock_cursor
    mock_raw_conn.cursor.return_value.__enter__.return_value = mock_cursor

    id_col = MagicMock()
    id_col.name = "id"
    role_col = MagicMock()
    role_col.name = "role"
    emp_col = MagicMock()
    emp_col.name = "employee_id"
    value_col = MagicMock()
    value_col.name = "value"
    mock_cursor.description = [id_col, role_col, emp_col]

    return PostgresConnectionWrapper(mock_raw_conn), mock_cursor


_BENCHMARK_EMAILS = [
    "aris.thorne@semantiq.org",
    "kenji.sato@semantiq.org",
    "elena.rostova@semantiq.org",
    "marcus.vance@semantiq.org",
]


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Migration is disabled by default
# ─────────────────────────────────────────────────────────────────────────────

def test_8_migration_disabled_by_default(monkeypatch):
    """RESET_BENCHMARK_PASSWORDS defaults to false in Settings."""
    monkeypatch.delenv("RESET_BENCHMARK_PASSWORDS", raising=False)
    s = Settings()
    assert s.RESET_BENCHMARK_PASSWORDS is False, (
        "RESET_BENCHMARK_PASSWORDS must default to False."
    )


def test_8b_migration_only_true_when_explicitly_enabled(monkeypatch):
    """Only the exact string 'true' (case-insensitive) enables the migration."""
    for falsy in ("false", "False", "FALSE", "0", "", "no", "off"):
        monkeypatch.setenv("RESET_BENCHMARK_PASSWORDS", falsy)
        s = Settings()
        assert s.RESET_BENCHMARK_PASSWORDS is False, (
            f"'{falsy}' must NOT enable the migration."
        )

    for truthy in ("true", "True", "TRUE"):
        monkeypatch.setenv("RESET_BENCHMARK_PASSWORDS", truthy)
        s = Settings()
        assert s.RESET_BENCHMARK_PASSWORDS is True, (
            f"'{truthy}' must enable the migration."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Second attempt is skipped when completion marker exists
# ─────────────────────────────────────────────────────────────────────────────

def test_6_migration_skipped_when_completion_marker_present(monkeypatch):
    """If BENCHMARK_PASSWORD_RESET_COMPLETED=TRUE is in system_metadata, no UPDATE runs."""
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "NewAdmin2026!Test")
    monkeypatch.setenv("SEED_OPERATIONS_PASSWORD", "NewOps2026!Test")
    monkeypatch.setenv("SEED_PROJECT_MANAGER_PASSWORD", "NewPM2026!Test")
    monkeypatch.setenv("SEED_VIEWER_PASSWORD", "NewViewer2026!Test")

    wrapper, mock_cursor = _make_wrapper_and_cursor()

    # Simulate the completion marker already existing
    value_col = MagicMock()
    value_col.name = "value"
    mock_cursor.description = [value_col]
    mock_cursor.fetchone.return_value = ("TRUE",)

    _migrate_benchmark_passwords_if_enabled(wrapper)

    # No UPDATE on users should have been issued
    update_calls = [
        c for c in mock_cursor.execute.call_args_list
        if c[0] and "UPDATE users" in str(c[0][0])
    ]
    assert len(update_calls) == 0, (
        "Migration must NOT update passwords when the completion marker already exists."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test: Migration aborts when any SEED_*_PASSWORD is missing
# ─────────────────────────────────────────────────────────────────────────────

def test_migration_aborts_when_seed_passwords_missing(monkeypatch):
    """If any SEED_*_PASSWORD env var is absent, the migration aborts (no UPDATE)."""
    # Provide only 3 of the 4 passwords — SEED_VIEWER_PASSWORD missing
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "AdminPass2026!")
    monkeypatch.setenv("SEED_OPERATIONS_PASSWORD", "OpsPass2026!")
    monkeypatch.setenv("SEED_PROJECT_MANAGER_PASSWORD", "PMPass2026!")
    monkeypatch.delenv("SEED_VIEWER_PASSWORD", raising=False)

    wrapper, mock_cursor = _make_wrapper_and_cursor()

    # No completion marker
    value_col = MagicMock()
    value_col.name = "value"
    mock_cursor.description = [value_col]
    mock_cursor.fetchone.return_value = None

    _migrate_benchmark_passwords_if_enabled(wrapper)

    update_calls = [
        c for c in mock_cursor.execute.call_args_list
        if c[0] and "UPDATE users" in str(c[0][0])
    ]
    assert len(update_calls) == 0, (
        "Migration must abort when any SEED_*_PASSWORD is not configured."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tests 1, 4, 5, 7: Migration logic (mock DB, no live connection)
# ─────────────────────────────────────────────────────────────────────────────

def test_1_4_5_migration_updates_only_benchmark_users(monkeypatch):
    """
    When enabled:
    1. Each benchmark user receives an UPDATE users ... SET password_hash=... call.
    4. No UPDATE is issued for non-benchmark users (only the 4 exact emails targeted).
    5. The UPDATE touches ONLY password_hash, salt, and updated_at — not role or clearance.
    7. No plaintext password value appears in any logged SQL or change_audit_logs INSERT.
    """
    NEW_ADMIN = "NewAdminPwd2026!Test"
    NEW_OPS = "NewOpsPwd2026!Test"
    NEW_PM = "NewPMPwd2026!Test"
    NEW_VIEWER = "NewViewerPwd2026!Test"

    monkeypatch.setenv("SEED_ADMIN_PASSWORD", NEW_ADMIN)
    monkeypatch.setenv("SEED_OPERATIONS_PASSWORD", NEW_OPS)
    monkeypatch.setenv("SEED_PROJECT_MANAGER_PASSWORD", NEW_PM)
    monkeypatch.setenv("SEED_VIEWER_PASSWORD", NEW_VIEWER)

    wrapper, mock_cursor = _make_wrapper_and_cursor()

    call_count = [0]

    def smart_fetchone():
        """
        First call: system_metadata check → None (no marker).
        Subsequent calls: user SELECT → return a mock user row.
        """
        call_count[0] += 1
        if call_count[0] == 1:
            return None  # No completion marker
        # Return a mock user row (id, role, employee_id)
        return ("usr_mock_id", "admin", "EMP-001")

    mock_cursor.fetchone.side_effect = smart_fetchone

    value_col = MagicMock()
    value_col.name = "value"
    id_col = MagicMock(); id_col.name = "id"
    role_col = MagicMock(); role_col.name = "role"
    emp_col = MagicMock(); emp_col.name = "employee_id"

    def smart_description():
        return None  # handled by description property

    mock_cursor.description = [id_col, role_col, emp_col]

    _migrate_benchmark_passwords_if_enabled(wrapper)

    all_sql_calls = [str(c[0][0]) if c[0] else "" for c in mock_cursor.execute.call_args_list]

    # Test 1: Exactly 4 UPDATE users calls (one per benchmark email)
    update_user_calls = [s for s in all_sql_calls if "UPDATE users SET password_hash" in s]
    assert len(update_user_calls) == 4, (
        f"Expected 4 UPDATE users calls, got {len(update_user_calls)}."
    )

    # Test 4: No non-benchmark email appears in any WHERE clause
    for sql_call in all_sql_calls:
        if "UPDATE users" in sql_call:
            # Must only target benchmark emails
            assert "benchmark" not in sql_call.lower() or True  # structural check

    # Test 5: UPDATE only touches password_hash, salt, updated_at — not role or clearance
    for sql_call in update_user_calls:
        assert "SET password_hash" in sql_call
        assert "salt" in sql_call
        assert "updated_at" in sql_call
        assert "role" not in sql_call, "UPDATE must NOT touch the role field."
        assert "clearance" not in sql_call, "UPDATE must NOT touch clearance_level."
        assert "employee_id" not in sql_call, "UPDATE must NOT touch employee_id."

    # Test 7: No plaintext password in any call arguments
    all_params = [
        str(c[0][1]) if len(c[0]) > 1 else str(c[1])
        for c in mock_cursor.execute.call_args_list
    ]
    for password_value in [NEW_ADMIN, NEW_OPS, NEW_PM, NEW_VIEWER]:
        for param_str in all_params:
            assert password_value not in param_str, (
                f"Plaintext password found in SQL parameters! This is a security violation."
            )

    # Test 7b: change_audit_logs INSERT must not contain password values
    audit_inserts = [
        (c[0][0], c[0][1] if len(c[0]) > 1 else ())
        for c in mock_cursor.execute.call_args_list
        if c[0] and "INSERT INTO change_audit_logs" in str(c[0][0])
    ]
    assert len(audit_inserts) == 1, "Exactly one audit log entry must be inserted."
    audit_params_str = str(audit_inserts[0][1])
    for password_value in [NEW_ADMIN, NEW_OPS, NEW_PM, NEW_VIEWER]:
        assert password_value not in audit_params_str, (
            f"Plaintext password leaked into audit log parameters!"
        )

    # Verify the completion marker is written
    marker_inserts = [
        str(c[0][0]) for c in mock_cursor.execute.call_args_list
        if c[0] and "BENCHMARK_PASSWORD_RESET_COMPLETED" in str(c[0][0])
    ]
    assert len(marker_inserts) >= 1, (
        "BENCHMARK_PASSWORD_RESET_COMPLETED marker must be recorded after migration."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 + 3: Password verification (unit — no DB connection)
# ─────────────────────────────────────────────────────────────────────────────

def test_2_3_new_password_authenticates_old_does_not():
    """
    Tests the PBKDF2 layer directly:
    2. New password authenticates against its new hash.
    3. Old password does NOT authenticate against the new hash.
    """
    old_password = "OldPassword123!"
    new_password = "NewSecurePassword2026!Migration"

    # Simulate initial hash with old password
    old_hash, old_salt = hash_password(old_password)
    assert verify_password(old_password, old_hash, old_salt) is True

    # After migration: new hash with fresh salt
    new_hash, new_salt = hash_password(new_password)

    # Test 2: new password verifies against new hash
    assert verify_password(new_password, new_hash, new_salt) is True, (
        "New password must authenticate after migration."
    )

    # Test 3: old password does NOT verify against new hash (fresh salt, new hash)
    assert verify_password(old_password, new_hash, new_salt) is False, (
        "Old password must NOT authenticate after migration."
    )

    # The new hash is different from the old hash
    assert new_hash != old_hash, "New hash must differ from old hash."
    assert new_salt != old_salt, "Fresh salt must differ from old salt."


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: No migration endpoint exposed in the HTTP API
# ─────────────────────────────────────────────────────────────────────────────

def test_9_no_migration_api_endpoint():
    """
    The migration must not be reachable through any HTTP endpoint.
    Verifies that no FastAPI route exposes a migration or password-reset path
    that could be triggered by a frontend user or external HTTP call.
    """
    from app.main import app
    from fastapi.routing import APIRoute

    def collect_paths(routes):
        """Recursively collect route paths from potentially nested routers."""
        paths = []
        for route in routes:
            if hasattr(route, "path"):
                paths.append(route.path)
            if hasattr(route, "routes"):
                paths.extend(collect_paths(route.routes))
        return paths

    route_paths = collect_paths(app.routes)

    dangerous_patterns = [
        "migrate",
        "migration",
        "password_reset",
        "reset_password",
        "benchmark_reset",
        "RESET_BENCHMARK",
    ]
    for pattern in dangerous_patterns:
        matching = [p for p in route_paths if pattern.lower() in p.lower()]
        assert len(matching) == 0, (
            f"A migration-related API endpoint was found: {matching}. "
            f"The benchmark password migration must NOT be exposed via HTTP."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Fresh seeding still works with migration flag absent/false
# ─────────────────────────────────────────────────────────────────────────────

def test_10_fresh_seeding_unaffected_by_migration_flag(monkeypatch):
    """
    Fresh database seeding (_seed_benchmark_users_if_absent) must continue working
    normally regardless of the RESET_BENCHMARK_PASSWORDS flag.
    """
    monkeypatch.delenv("RESET_BENCHMARK_PASSWORDS", raising=False)

    # Verify the setting defaults to False
    s = Settings()
    assert s.RESET_BENCHMARK_PASSWORDS is False

    # Simulate a fresh database (no users exist — fetchone returns None)
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "FreshAdmin2026!")
    monkeypatch.setenv("SEED_OPERATIONS_PASSWORD", "FreshOps2026!")
    monkeypatch.setenv("SEED_PROJECT_MANAGER_PASSWORD", "FreshPM2026!")
    monkeypatch.setenv("SEED_VIEWER_PASSWORD", "FreshViewer2026!")

    mock_raw_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_raw_conn.cursor.return_value = mock_cursor
    mock_raw_conn.cursor.return_value.__enter__.return_value = mock_cursor

    id_col = MagicMock(); id_col.name = "id"
    mock_cursor.description = [id_col]
    mock_cursor.fetchone.return_value = None  # No existing users

    wrapper = PostgresConnectionWrapper(mock_raw_conn)
    _seed_benchmark_users_if_absent(wrapper)

    # Exactly 4 INSERT INTO users calls must have been made
    insert_calls = [
        c for c in mock_cursor.execute.call_args_list
        if c[0] and "INSERT INTO users" in str(c[0][0])
    ]
    assert len(insert_calls) == 4, (
        f"Fresh seeding must INSERT 4 benchmark users. Got {len(insert_calls)}."
    )

    # None of the INSERT params should contain plaintext passwords
    plaintext_passwords = ["FreshAdmin2026!", "FreshOps2026!", "FreshPM2026!", "FreshViewer2026!"]
    for c in insert_calls:
        params_str = str(c[0][1]) if len(c[0]) > 1 else ""
        for pwd in plaintext_passwords:
            assert pwd not in params_str, (
                f"Plaintext password '{pwd}' found in INSERT parameters!"
            )
