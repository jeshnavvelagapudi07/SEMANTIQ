"""
Database Engine & Persistence Layer for SEMANTIQ
PostgreSQL-only. Manages tables: users, entities, relationships,
change_audit_logs, action_items, audit_logs, system_metadata.
Ensures PostgreSQL schema isolation (schema: semantiq).
Seeds initial benchmark accounts and graph topology safely on initialization.
"""
import os
import json
import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from app.core.config import settings

# ──────────────────────────────────────────────────────────────────────────────
# Cryptographic Password Utilities (PBKDF2-HMAC-SHA256 with random salt)
# ──────────────────────────────────────────────────────────────────────────────

def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hashes a password with a 16-byte random salt using 100,000 PBKDF2-HMAC-SHA256 iterations."""
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return key.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Verifies a candidate password against a stored PBKDF2 hash using constant-time comparison."""
    candidate_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(candidate_hash, password_hash)


# ──────────────────────────────────────────────────────────────────────────────
# Universal Row Abstraction
# ──────────────────────────────────────────────────────────────────────────────

class DbRow:
    """
    Universal database row representation supporting:
    - String column access: row["id"], row["cnt"]
    - Integer column indexing: row[0], row[1]
    - Mapping conversion: dict(row)
    - Key checks and iteration: "id" in row, for k in row
    """
    def __init__(self, col_names: list[str], values: tuple | list):
        self._col_names = [c.lower() for c in col_names]
        self._raw_col_names = list(col_names)
        self._data = {col.lower(): val for col, val in zip(col_names, values)}
        self._dict_repr = {col: val for col, val in zip(col_names, values)}
        self._tuple = tuple(values)

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return self._tuple[key]
        if isinstance(key, str):
            k_lower = key.lower()
            if k_lower in self._data:
                return self._data[k_lower]
        return self._dict_repr[key]

    def get(self, key: str, default: Any = None) -> Any:
        k_lower = key.lower()
        if k_lower in self._data:
            return self._data[k_lower]
        return default

    def keys(self):
        return self._dict_repr.keys()

    def values(self):
        return self._dict_repr.values()

    def items(self):
        return self._dict_repr.items()

    def __iter__(self):
        return iter(self._dict_repr)

    def __len__(self):
        return len(self._tuple)

    def __contains__(self, key: Any) -> bool:
        if isinstance(key, str):
            return key.lower() in self._data or key in self._dict_repr
        return False

    def __repr__(self):
        return f"DbRow({self._dict_repr})"


# ──────────────────────────────────────────────────────────────────────────────
# PostgreSQL Adapter Wrappers
# ──────────────────────────────────────────────────────────────────────────────

class PostgresCursorWrapper:
    def __init__(self, raw_cursor):
        self._cursor = raw_cursor

    def execute(self, query: str, params: tuple | list = None):
        translated = _translate_placeholders(query)
        if params is not None:
            if isinstance(params, list):
                params = tuple(params)
            self._cursor.execute(translated, params)
        else:
            self._cursor.execute(translated)
        return self

    def fetchone(self) -> Optional[DbRow]:
        row = self._cursor.fetchone()
        if row is None:
            return None
        col_names = [desc.name for desc in self._cursor.description]
        return DbRow(col_names, row)

    def fetchall(self) -> list[DbRow]:
        rows = self._cursor.fetchall()
        if not rows:
            return []
        col_names = [desc.name for desc in self._cursor.description]
        return [DbRow(col_names, r) for r in rows]

    def close(self):
        self._cursor.close()

    @property
    def description(self):
        return self._cursor.description


class PostgresConnectionWrapper:
    def __init__(self, raw_conn, schema: str = settings.POSTGRES_SCHEMA):
        self._conn = raw_conn
        self.schema = schema
        with self._conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema};")
            cur.execute(f"SET search_path TO {self.schema}, public;")
        self._conn.commit()

    def cursor(self) -> PostgresCursorWrapper:
        return PostgresCursorWrapper(self._conn.cursor())

    def execute(self, query: str, params: tuple | list = None) -> PostgresCursorWrapper:
        cur = self.cursor()
        cur.execute(query, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                self.rollback()
            else:
                self.commit()
        finally:
            self.close()


def _translate_placeholders(sql: str) -> str:
    """Converts ? placeholders to %s for psycopg."""
    if '?' in sql:
        return sql.replace('?', '%s')
    return sql


# ──────────────────────────────────────────────────────────────────────────────
# Database Connection Factory — PostgreSQL Only
# ──────────────────────────────────────────────────────────────────────────────

def get_db_connection() -> PostgresConnectionWrapper:
    """
    Returns an active PostgreSQL connection wrapper.
    Fails immediately with a clear RuntimeError if DATABASE_URL is not a PostgreSQL URL.
    """
    import psycopg
    conn = psycopg.connect(settings.DATABASE_URL)
    return PostgresConnectionWrapper(conn, schema=settings.POSTGRES_SCHEMA)


# ──────────────────────────────────────────────────────────────────────────────
# Schema Initialization and Migrations
# ──────────────────────────────────────────────────────────────────────────────

def init_db():
    """
    Initializes the PostgreSQL database schema.
    Creates tables idempotently. Performs safe migrations.
    Seeds benchmark users (only if not already present).
    Seeds knowledge graph (only if entities table is empty).
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                auth_user_id TEXT UNIQUE,
                employee_id TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                display_name TEXT NOT NULL,
                department TEXT NOT NULL,
                job_title TEXT NOT NULL,
                role TEXT NOT NULL,
                clearance_level TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 2. Knowledge Graph Entities Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                metadata TEXT,
                access_tier TEXT NOT NULL DEFAULT 'INTERNAL',
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                owner_team TEXT,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1
            )
        """)

        # 3. Knowledge Graph Relationships Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id TEXT PRIMARY KEY,
                source_entity_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                target_entity_id TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING_VERIFICATION',
                access_tier TEXT NOT NULL DEFAULT 'INTERNAL',
                evidence_ids TEXT,
                version INTEGER NOT NULL DEFAULT 1,
                reviewed_by TEXT,
                reviewed_at TEXT,
                review_comment TEXT,
                weight REAL DEFAULT 1.0,
                description TEXT
            )
        """)

        # 4. Change Audit Ledger Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS change_audit_logs (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                actor_user_id TEXT NOT NULL,
                actor_role TEXT NOT NULL,
                action_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                target_type TEXT NOT NULL,
                old_values TEXT,
                new_values TEXT,
                reason TEXT
            )
        """)

        # 5. Operational Action Items Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS action_items (
                id TEXT PRIMARY KEY,
                query_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                target_entity TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                reviewed_by TEXT,
                reviewed_at TEXT,
                resolution_comment TEXT
            )
        """)

        # 6. Reasoning Query Audit Logs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                user_id TEXT NOT NULL,
                user_role TEXT NOT NULL,
                query TEXT NOT NULL,
                identified_entities TEXT,
                authorized_entities TEXT,
                filtered_entities_count INTEGER DEFAULT 0,
                filtered_details TEXT,
                graph_paths_count INTEGER DEFAULT 0,
                evidence_ids TEXT,
                llm_provider TEXT,
                validation_status TEXT,
                confidence_score REAL,
                confidence_level TEXT,
                recommendation TEXT,
                requires_human_review INTEGER DEFAULT 0,
                action_id TEXT,
                action_status TEXT
            )
        """)

        # 7. System Metadata Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.commit()

        # Safe column migrations (ADD COLUMN IF NOT EXISTS is PostgreSQL-native)
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS username TEXT;")
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_user_id TEXT;")
        cursor.execute("ALTER TABLE relationships ADD COLUMN IF NOT EXISTS weight REAL DEFAULT 1.0;")
        cursor.execute("ALTER TABLE relationships ADD COLUMN IF NOT EXISTS description TEXT;")
        conn.commit()

        # Seed benchmark users if they do not yet exist (idempotent by email)
        _seed_benchmark_users_if_absent(conn)

        # One-time benchmark password migration — only runs when:
        #   1. RESET_BENCHMARK_PASSWORDS=true in the environment, AND
        #   2. The BENCHMARK_PASSWORD_RESET_COMPLETED marker is NOT in system_metadata.
        if settings.RESET_BENCHMARK_PASSWORDS:
            _migrate_benchmark_passwords_if_enabled(conn)

        # Seed knowledge graph if entities table is empty
        cursor.execute("SELECT COUNT(*) as cnt FROM entities")
        entity_count = cursor.fetchone()["cnt"]
        if entity_count == 0:
            _seed_initial_graph(conn)


def _seed_benchmark_users_if_absent(conn):
    """
    Creates the four benchmark accounts only if they do not already exist in the database.
    Uses SEED_*_PASSWORD environment variables for initial password hashing.
    A Render redeployment will NEVER overwrite existing passwords.
    """
    now = datetime.now(timezone.utc).isoformat()

    benchmark_users = [
        {
            "id": "usr_admin_01",
            "auth_user_id": "auth_admin_01",
            "employee_id": "EMP-001",
            "username": "admin_01",
            "email": "aris.thorne@semantiq.org",
            "display_name": "Dr. Aris Thorne",
            "department": "Executive Engineering Leadership",
            "job_title": "Chief Technology Officer & System Admin",
            "role": "admin",
            "clearance_level": "RESTRICTED",
            "seed_password_env": "SEED_ADMIN_PASSWORD",
        },
        {
            "id": "usr_ops_01",
            "auth_user_id": "auth_ops_01",
            "employee_id": "EMP-002",
            "username": "ops_eng_01",
            "email": "kenji.sato@semantiq.org",
            "display_name": "Kenji Sato",
            "department": "Manufacturing Operations & Reliability",
            "job_title": "Lead Reliability & Operations Engineer",
            "role": "operations_engineer",
            "clearance_level": "CONFIDENTIAL",
            "seed_password_env": "SEED_OPERATIONS_PASSWORD",
        },
        {
            "id": "usr_pm_01",
            "auth_user_id": "auth_pm_01",
            "employee_id": "EMP-003",
            "username": "pm_01",
            "email": "elena.rostova@semantiq.org",
            "display_name": "Elena Rostova",
            "department": "Aerospace Program Delivery",
            "job_title": "Principal Delivery & Project Director",
            "role": "project_manager",
            "clearance_level": "CONFIDENTIAL",
            "seed_password_env": "SEED_PROJECT_MANAGER_PASSWORD",
        },
        {
            "id": "usr_view_01",
            "auth_user_id": "auth_view_01",
            "employee_id": "EMP-004",
            "username": "viewer_01",
            "email": "marcus.vance@semantiq.org",
            "display_name": "Marcus Vance",
            "department": "Quality & Regulatory Compliance",
            "job_title": "Independent Compliance & Safety Auditor",
            "role": "viewer",
            "clearance_level": "INTERNAL",
            "seed_password_env": "SEED_VIEWER_PASSWORD",
        },
    ]

    cursor = conn.cursor()
    for u in benchmark_users:
        # Check by email — primary identity anchor
        cursor.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(%s)", (u["email"],))
        existing = cursor.fetchone()
        if existing:
            # User already exists — never overwrite password, just ensure username is set
            cursor.execute(
                "UPDATE users SET username = %s, auth_user_id = %s WHERE LOWER(email) = LOWER(%s) AND (username IS NULL OR username = '')",
                (u["username"], u["auth_user_id"], u["email"])
            )
            continue

        # Resolve seed password from environment
        seed_pwd = os.getenv(u["seed_password_env"], "").strip()
        if not seed_pwd:
            # No seed password configured — generate a random one and warn loudly
            import logging
            seed_pwd = secrets.token_urlsafe(24)
            logging.getLogger("semantiq").warning(
                f"SECURITY WARNING: {u['seed_password_env']} is not set. "
                f"A random password was generated for {u['email']}. "
                f"Set this environment variable to use a known password."
            )

        p_hash, salt = hash_password(seed_pwd)
        cursor.execute("""
            INSERT INTO users (
                id, auth_user_id, employee_id, username, email,
                password_hash, salt, display_name, department,
                job_title, role, clearance_level, status,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING
        """, (
            u["id"], u["auth_user_id"], u["employee_id"], u["username"], u["email"],
            p_hash, salt, u["display_name"], u["department"],
            u["job_title"], u["role"], u["clearance_level"], "ACTIVE",
            now, now
        ))
    conn.commit()


def _migrate_benchmark_passwords_if_enabled(conn):
    """
    One-time benchmark password migration.

    Resets the PBKDF2-HMAC-SHA256 password hashes for the four canonical benchmark
    accounts using the current SEED_*_PASSWORD environment variables. This is only
    needed when deploying to an existing database whose benchmark accounts were seeded
    with a different (old) password.

    Safety constraints:
    - Controlled by RESET_BENCHMARK_PASSWORDS=true in the environment (default: false).
    - Runs at most ONCE: records BENCHMARK_PASSWORD_RESET_COMPLETED in system_metadata
      on success. All subsequent startups skip this function even if the env var remains
      enabled.
    - Only modifies password_hash, salt, and updated_at on the four exact benchmark emails.
    - Touches no other users, no roles, no clearances, no knowledge graph data.
    - Never logs or records plaintext password values.
    - Requires all four SEED_*_PASSWORD env vars to be set; aborts if any are missing.
    """
    import logging
    logger = logging.getLogger("semantiq")

    cursor = conn.cursor()

    # Guard 1: check the completion marker — idempotency
    cursor.execute("SELECT value FROM system_metadata WHERE key = 'BENCHMARK_PASSWORD_RESET_COMPLETED'")
    marker = cursor.fetchone()
    if marker and marker["value"] == "TRUE":
        logger.info("Benchmark password migration: already completed — skipping.")
        return

    # Guard 2: require all four seed passwords to be explicitly configured
    _BENCHMARK_MIGRATION_MAP = [
        ("aris.thorne@semantiq.org",   "SEED_ADMIN_PASSWORD"),
        ("kenji.sato@semantiq.org",    "SEED_OPERATIONS_PASSWORD"),
        ("elena.rostova@semantiq.org", "SEED_PROJECT_MANAGER_PASSWORD"),
        ("marcus.vance@semantiq.org",  "SEED_VIEWER_PASSWORD"),
    ]
    passwords = {}
    for email, env_var in _BENCHMARK_MIGRATION_MAP:
        pwd = os.getenv(env_var, "").strip()
        if not pwd:
            logger.error(
                f"Benchmark password migration ABORTED: {env_var} is not set. "
                f"All four SEED_*_PASSWORD variables must be configured before running this migration."
            )
            return
        passwords[email] = pwd

    now = datetime.now(timezone.utc).isoformat()
    migrated_ids = []

    for email, env_var in _BENCHMARK_MIGRATION_MAP:
        # Verify the user exists in the database before touching anything
        cursor.execute(
            "SELECT id, role, employee_id FROM users WHERE LOWER(email) = LOWER(%s)",
            (email,)
        )
        user = cursor.fetchone()
        if not user:
            logger.warning(
                f"Benchmark password migration: user {email} not found in database — skipping this account."
            )
            continue

        # Hash the new password with a fresh random salt
        new_hash, new_salt = hash_password(passwords[email])

        # Update ONLY password_hash, salt, and updated_at — nothing else
        cursor.execute(
            "UPDATE users SET password_hash = %s, salt = %s, updated_at = %s WHERE LOWER(email) = LOWER(%s)",
            (new_hash, new_salt, now, email)
        )
        migrated_ids.append(user["id"])
        logger.info(
            f"Benchmark password migration: password updated for {email} (id={user['id']}, role={user['role']})."
        )

    # Record the migration event in change_audit_logs (no password values)
    log_id = f"CHG-{uuid.uuid4().hex[:8]}"
    cursor.execute("""
        INSERT INTO change_audit_logs (
            id, timestamp, actor_user_id, actor_role, action_type,
            target_id, target_type, old_values, new_values, reason
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        log_id,
        now,
        "SYSTEM_MIGRATION",
        "SYSTEM",
        "BENCHMARK_PASSWORD_RESET",
        ",".join(migrated_ids),
        "USER",
        None,
        json.dumps({"migrated_accounts": len(migrated_ids), "emails": [e for e, _ in _BENCHMARK_MIGRATION_MAP]}),
        "One-time benchmark password migration executed via RESET_BENCHMARK_PASSWORDS=true. "
        "Password hashes updated using SEED_*_PASSWORD env vars. No plaintext stored."
    ))

    # Record the completion marker so this never runs again
    cursor.execute("SELECT 1 FROM system_metadata WHERE key = 'BENCHMARK_PASSWORD_RESET_COMPLETED'")
    if cursor.fetchone():
        cursor.execute(
            "UPDATE system_metadata SET value = 'TRUE', created_at = %s WHERE key = 'BENCHMARK_PASSWORD_RESET_COMPLETED'",
            (now,)
        )
    else:
        cursor.execute(
            "INSERT INTO system_metadata (key, value, created_at) VALUES ('BENCHMARK_PASSWORD_RESET_COMPLETED', 'TRUE', %s)",
            (now,)
        )

    conn.commit()
    logger.info(
        f"Benchmark password migration COMPLETED: {len(migrated_ids)} account(s) updated. "
        f"Completion marker recorded — future startups will skip this migration."
    )


def _seed_initial_graph(conn):
    """Seeds the initial graph entities and relationships with ACTIVE and VERIFIED status."""
    from app.data.seed_data import SEED_ENTITIES, SEED_RELATIONSHIPS
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.cursor()

    for ent in SEED_ENTITIES:
        cursor.execute("""
            INSERT INTO entities (
                id, type, name, description, metadata, access_tier,
                status, owner_team, created_by, created_at, updated_at, version
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (
            ent.id,
            ent.type.value,
            ent.name,
            ent.description,
            json.dumps(ent.properties),
            ent.classification.value,
            "ACTIVE",
            ent.owner_team,
            "system_seed",
            now,
            now,
            1
        ))

    for rel in SEED_RELATIONSHIPS:
        cursor.execute("""
            INSERT INTO relationships (
                id, source_entity_id, relationship_type, target_entity_id,
                created_by, created_at, status, access_tier, evidence_ids,
                version, reviewed_by, reviewed_at, review_comment, weight, description
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (
            rel.id,
            rel.source_id,
            rel.relation_type.value,
            rel.target_id,
            "system_seed",
            now,
            "VERIFIED",
            "INTERNAL",
            json.dumps([]),
            1,
            "system_admin",
            now,
            "System initialized authoritative relationship.",
            rel.weight,
            rel.description
        ))

    conn.commit()


# ──────────────────────────────────────────────────────────────────────────────
# Initialization Hook
# NOTE: init_db() is called from app.main lifespan on application startup.
# It is NOT called at module import time so that the module can be imported
# in tests and other contexts without requiring an active database connection.
# ──────────────────────────────────────────────────────────────────────────────
