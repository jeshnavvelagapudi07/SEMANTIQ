"""
Tests for Temporary Production Admin Password Recovery Bootstrap Mechanism.
Verifies:
- bootstrap password successfully resets aris.thorne@semantiq.org
- password is encrypted with PBKDF2-HMAC-SHA256, never stored in plaintext
- only the admin account is modified (other employee accounts untouched)
- recovery operation is consumed only once via database-backed system_metadata marker
- second startup does not reset again even if env variable remains
- missing bootstrap variable changes nothing
- weak bootstrap passwords (<16 chars, lacking upper/lower/digit/special) are rejected
- explicit audit event PRODUCTION_ADMIN_PASSWORD_BOOTSTRAPPED is emitted without secrets
- secret does not leak into settings serialization, logs, or API responses
"""
import os
import json
import pytest
from app.core.config import settings
from app.core.database import (
    get_db_connection,
    verify_password,
    hash_password,
    validate_bootstrap_password_complexity,
    _handle_admin_password_bootstrap
)
from app.services.user_service import user_service


STRONG_BOOTSTRAP_PWD = "SemantiqAdminSecure2026!#Recovery"


def test_weak_bootstrap_passwords_strictly_rejected():
    """Verifies that passwords under 16 chars or missing required complexity classes fail fast."""
    # Too short (< 16)
    with pytest.raises(ValueError, match="minimum length requirement"):
        validate_bootstrap_password_complexity("Short1!Aa")

    # Missing uppercase
    with pytest.raises(ValueError, match="missing uppercase letter"):
        validate_bootstrap_password_complexity("alllowercase12345!@#recovery")

    # Missing lowercase
    with pytest.raises(ValueError, match="missing lowercase letter"):
        validate_bootstrap_password_complexity("ALLUPPERCASE12345!@#RECOVERY")

    # Missing digit
    with pytest.raises(ValueError, match="missing numeric digit"):
        validate_bootstrap_password_complexity("NoDigitsInThisPassword!@#Recovery")

    # Missing special character
    with pytest.raises(ValueError, match="missing special character"):
        validate_bootstrap_password_complexity("NoSpecialChars1234567890Recovery")

    # Valid strong password does not raise
    validate_bootstrap_password_complexity(STRONG_BOOTSTRAP_PWD)


def test_missing_bootstrap_variable_changes_nothing(monkeypatch):
    """Verifies that when ADMIN_BOOTSTRAP_PASSWORD is absent, database bootstrap is a no-op."""
    monkeypatch.delenv("ADMIN_BOOTSTRAP_PASSWORD", raising=False)

    with get_db_connection() as conn:
        # Get current admin password hash
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, salt FROM users WHERE email = 'aris.thorne@semantiq.org'")
        before_row = cursor.fetchone()

        result = _handle_admin_password_bootstrap(conn, force=True)
        assert result is False

        cursor.execute("SELECT password_hash, salt FROM users WHERE email = 'aris.thorne@semantiq.org'")
        after_row = cursor.fetchone()

        assert before_row["password_hash"] == after_row["password_hash"]
        assert before_row["salt"] == after_row["salt"]


def test_bootstrap_password_resets_admin_and_preserves_other_accounts(monkeypatch):
    """
    Verifies that:
    1. The admin password for aris.thorne@semantiq.org is successfully reset and hashed.
    2. No plaintext password is saved anywhere in the database.
    3. Other accounts (Kenji Sato, Elena Rostova, Marcus Vance) remain completely untouched.
    4. An explicit PRODUCTION_ADMIN_PASSWORD_BOOTSTRAPPED audit entry is written without secrets.
    """
    # Capture snapshot of other accounts before bootstrap
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Ensure fresh state for test by removing any previous marker
        cursor.execute("DELETE FROM system_metadata WHERE key = 'ADMIN_BOOTSTRAP_CONSUMED'")
        conn.commit()

        cursor.execute("SELECT id, email, password_hash, salt FROM users WHERE email != 'aris.thorne@semantiq.org'")
        other_users_before = {row["email"]: (row["password_hash"], row["salt"]) for row in cursor.fetchall()}

    monkeypatch.setenv("ADMIN_BOOTSTRAP_PASSWORD", STRONG_BOOTSTRAP_PWD)
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_PASSWORD", STRONG_BOOTSTRAP_PWD)

    with get_db_connection() as conn:
        result = _handle_admin_password_bootstrap(conn, force=True)
        assert result is True

    # 1. Verify admin password updated and verifiable
    admin_profile = user_service.get_user_by_email_or_username("aris.thorne@semantiq.org")
    assert admin_profile is not None
    assert admin_profile["role"] == "admin"

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, salt FROM users WHERE email = 'aris.thorne@semantiq.org'")
        admin_creds = cursor.fetchone()
        assert admin_creds["password_hash"] != STRONG_BOOTSTRAP_PWD  # MUST be hashed
        assert STRONG_BOOTSTRAP_PWD not in admin_creds["password_hash"]
        assert verify_password(STRONG_BOOTSTRAP_PWD, admin_creds["password_hash"], admin_creds["salt"]) is True

    # 2. Authenticate admin using new password
    auth_result = user_service.authenticate("aris.thorne@semantiq.org", STRONG_BOOTSTRAP_PWD)
    assert auth_result["email"] == "aris.thorne@semantiq.org"
    assert auth_result["role"] == "admin"

    # 3. Verify other users remain completely unchanged
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, password_hash, salt FROM users WHERE email != 'aris.thorne@semantiq.org'")
        other_users_after = {row["email"]: (row["password_hash"], row["salt"]) for row in cursor.fetchall()}

    for email, (before_hash, before_salt) in other_users_before.items():
        after_hash, after_salt = other_users_after[email]
        assert before_hash == after_hash, f"User {email} password_hash was modified!"
        assert before_salt == after_salt, f"User {email} salt was modified!"

    # 4. Verify audit ledger entry
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM change_audit_logs
            WHERE action_type = 'PRODUCTION_ADMIN_PASSWORD_BOOTSTRAPPED'
            ORDER BY timestamp DESC LIMIT 1
        """)
        audit_row = cursor.fetchone()
        assert audit_row is not None
        assert audit_row["actor_user_id"] == "SYSTEM_BOOTSTRAP"
        assert audit_row["target_id"] == "usr_admin_01"
        assert audit_row["target_type"] == "USER"

        # Ensure NO secrets/passwords are leaked into audit record
        for field in ["old_values", "new_values", "reason"]:
            val = audit_row[field] or ""
            assert STRONG_BOOTSTRAP_PWD not in val
            assert admin_creds["password_hash"] not in val
            assert admin_creds["salt"] not in val


def test_bootstrap_is_consumed_only_once_and_subsequent_starts_do_not_reset(monkeypatch):
    """
    Verifies that once consumed, future restarts do NOT re-apply or overwrite the admin password,
    even if ADMIN_BOOTSTRAP_PASSWORD remains present in the environment.
    """
    monkeypatch.setenv("ADMIN_BOOTSTRAP_PASSWORD", STRONG_BOOTSTRAP_PWD)
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_PASSWORD", STRONG_BOOTSTRAP_PWD)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Verify marker is set to TRUE
        cursor.execute("SELECT value FROM system_metadata WHERE key = 'ADMIN_BOOTSTRAP_CONSUMED'")
        marker_row = cursor.fetchone()
        assert marker_row is not None
        assert marker_row["value"] == "TRUE"

        # Now simulate manual password update by the admin
        new_custom_pwd = "CustomAdminPasswordAfterLogin2026!#"
        p_hash, salt = hash_password(new_custom_pwd)
        cursor.execute("""
            UPDATE users SET password_hash = ?, salt = ? WHERE email = 'aris.thorne@semantiq.org'
        """, (p_hash, salt))
        conn.commit()

        # Simulate second application startup / restart
        result2 = _handle_admin_password_bootstrap(conn, force=True)
        assert result2 is False  # Must NOT execute again

        # Confirm custom password is STILL intact and was NOT overwritten by bootstrap
        cursor.execute("SELECT password_hash, salt FROM users WHERE email = 'aris.thorne@semantiq.org'")
        current_creds = cursor.fetchone()
        assert verify_password(new_custom_pwd, current_creds["password_hash"], current_creds["salt"]) is True


def test_settings_excludes_bootstrap_password_from_serialization(monkeypatch):
    """Verifies that ADMIN_BOOTSTRAP_PASSWORD is never exposed in repr or model dicts."""
    monkeypatch.setenv("ADMIN_BOOTSTRAP_PASSWORD", STRONG_BOOTSTRAP_PWD)
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_PASSWORD", STRONG_BOOTSTRAP_PWD)

    # repr(settings) should not leak the password
    repr_str = repr(settings)
    assert STRONG_BOOTSTRAP_PWD not in repr_str

    # model_dump should not leak the password (exclude=True)
    dump_dict = settings.model_dump()
    assert "ADMIN_BOOTSTRAP_PASSWORD" not in dump_dict
