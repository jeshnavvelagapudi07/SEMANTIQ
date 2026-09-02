"""
Database Engine & Persistence Layer for SEMANTIQ
Supports SQLite (local development/testing) and PostgreSQL (production deployment on Render).
Manages tables: users, entities, relationships, change_audit_logs, action_items, and audit_logs.
Ensures PostgreSQL schema isolation (schema: semantiq) so tables never collide with shared databases.
Seeds initial benchmark accounts and graph topology safely on initialization.
"""
import sqlite3
import os
import re
import json
import hashlib
import secrets
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
# Universal SQL Translation & Row Abstraction
# ──────────────────────────────────────────────────────────────────────────────

def translate_sql_for_postgres(sql: str) -> str:
    """
    Translates standard/SQLite SQL dialect to PostgreSQL dialect:
    - Converts '?' parameter placeholders to '%s'
    - Converts 'INSERT OR IGNORE INTO' to 'INSERT INTO ... ON CONFLICT DO NOTHING'
    """
    out = sql
    if '?' in out:
        out = out.replace('?', '%s')
    if 'INSERT OR IGNORE INTO' in out.upper():
        out = re.sub(r'INSERT\s+OR\s+IGNORE\s+INTO', 'INSERT INTO', out, flags=re.IGNORECASE)
        if 'ON CONFLICT' not in out.upper():
            out = out.rstrip().rstrip(';') + ' ON CONFLICT DO NOTHING'
    return out


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
        translated = translate_sql_for_postgres(query)
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


# ──────────────────────────────────────────────────────────────────────────────
# SQLite Adapter Wrappers
# ──────────────────────────────────────────────────────────────────────────────

class SqliteConnectionWrapper:
    def __init__(self, raw_conn: sqlite3.Connection):
        self._conn = raw_conn

    def cursor(self) -> sqlite3.Cursor:
        return self._conn.cursor()

    def execute(self, query: str, params: tuple | list = None) -> sqlite3.Cursor:
        if params is not None:
            return self._conn.execute(query, params)
        return self._conn.execute(query)

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


# ──────────────────────────────────────────────────────────────────────────────
# Database Connection Factory
# ──────────────────────────────────────────────────────────────────────────────

def get_db_connection():
    """
    Returns an active database connection wrapper supporting both SQLite and PostgreSQL.
    - If DATABASE_URL is PostgreSQL: connects with psycopg, isolates schema to 'semantiq'.
    - If DATABASE_URL is SQLite: connects with sqlite3, enables WAL mode.
    """
    if settings.is_postgres:
        import psycopg
        conn = psycopg.connect(settings.DATABASE_URL)
        return PostgresConnectionWrapper(conn, schema=settings.POSTGRES_SCHEMA)
    else:
        db_path = settings.DATABASE_PATH
        conn = sqlite3.connect(db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        return SqliteConnectionWrapper(conn)


# ──────────────────────────────────────────────────────────────────────────────
# Schema Initialization and Migrations
# ──────────────────────────────────────────────────────────────────────────────

def init_db():
    """
    Initializes the database schema for both SQLite and PostgreSQL.
    Creates tables: users, entities, relationships, change_audit_logs, action_items, audit_logs.
    Performs non-destructive schema migrations and seeds initial accounts and graph topology.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Users Table (Enterprise multi-employee identity)
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

        conn.commit()

        # Database Dialect Specific Column Migrations
        if settings.is_postgres:
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS username TEXT;")
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_user_id TEXT;")
            cursor.execute("ALTER TABLE relationships ADD COLUMN IF NOT EXISTS weight REAL DEFAULT 1.0;")
            cursor.execute("ALTER TABLE relationships ADD COLUMN IF NOT EXISTS description TEXT;")
        else:
            cursor.execute("PRAGMA table_info(users)")
            existing_cols = {row[1] for row in cursor.fetchall()}
            if "username" not in existing_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
            if "auth_user_id" not in existing_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN auth_user_id TEXT")

            cursor.execute("PRAGMA table_info(relationships)")
            existing_rel_cols = {row[1] for row in cursor.fetchall()}
            if "weight" not in existing_rel_cols:
                cursor.execute("ALTER TABLE relationships ADD COLUMN weight REAL DEFAULT 1.0")
            if "description" not in existing_rel_cols:
                cursor.execute("ALTER TABLE relationships ADD COLUMN description TEXT")

        conn.commit()

        # Update legacy persona records with canonical usernames if needed
        cursor.execute("""
            UPDATE users SET username = 'ops_eng_01', auth_user_id = 'auth_ops_01' WHERE id = 'usr_ops_01' AND (username IS NULL OR username = '')
        """)
        cursor.execute("""
            UPDATE users SET username = 'pm_01', auth_user_id = 'auth_pm_01' WHERE id = 'usr_pm_01' AND (username IS NULL OR username = '')
        """)
        cursor.execute("""
            UPDATE users SET username = 'viewer_01', auth_user_id = 'auth_view_01' WHERE id = 'usr_view_01' AND (username IS NULL OR username = '')
        """)
        cursor.execute("""
            UPDATE users SET username = 'admin_01', auth_user_id = 'auth_admin_01' WHERE id = 'usr_admin_01' AND (username IS NULL OR username = '')
        """)
        conn.commit()

        # Seed Initial Development/Demo Users if table is empty
        cursor.execute("SELECT COUNT(*) as cnt FROM users")
        user_count = cursor.fetchone()["cnt"]
        if user_count == 0:
            _seed_initial_users(conn)

        # Seed Initial Knowledge Graph if entities table is empty
        cursor.execute("SELECT COUNT(*) as cnt FROM entities")
        entity_count = cursor.fetchone()["cnt"]
        if entity_count == 0:
            _seed_initial_graph(conn)


def _seed_initial_users(conn):
    """Seeds the 4 pre-configured development/benchmark personas with salted hashes."""
    now = datetime.now(timezone.utc).isoformat()
    dev_password = "Password123!" if settings.APP_ENV != "production" else secrets.token_urlsafe(24)

    initial_users = [
        {
            "id": "usr_ops_01",
            "auth_user_id": "auth_ops_01",
            "employee_id": "EMP-001",
            "username": "ops_eng_01",
            "email": "kenji.sato@semantiq.org",
            "display_name": "Kenji Sato",
            "department": "Manufacturing Operations & Reliability",
            "job_title": "Lead Reliability & Operations Engineer",
            "role": "operations_engineer",
            "clearance_level": "CONFIDENTIAL",
            "status": "ACTIVE"
        },
        {
            "id": "usr_pm_01",
            "auth_user_id": "auth_pm_01",
            "employee_id": "EMP-002",
            "username": "pm_01",
            "email": "elena.rostova@semantiq.org",
            "display_name": "Elena Rostova",
            "department": "Aerospace Program Delivery",
            "job_title": "Principal Delivery & Project Director",
            "role": "project_manager",
            "clearance_level": "CONFIDENTIAL",
            "status": "ACTIVE"
        },
        {
            "id": "usr_view_01",
            "auth_user_id": "auth_view_01",
            "employee_id": "EMP-003",
            "username": "viewer_01",
            "email": "marcus.vance@semantiq.org",
            "display_name": "Marcus Vance",
            "department": "Quality & Regulatory Compliance",
            "job_title": "Independent Compliance & Safety Auditor",
            "role": "viewer",
            "clearance_level": "INTERNAL",
            "status": "ACTIVE"
        },
        {
            "id": "usr_admin_01",
            "auth_user_id": "auth_admin_01",
            "employee_id": "EMP-004",
            "username": "admin_01",
            "email": "aris.thorne@semantiq.org",
            "display_name": "Dr. Aris Thorne",
            "department": "Executive Engineering Leadership",
            "job_title": "Chief Technology Officer & System Admin",
            "role": "admin",
            "clearance_level": "RESTRICTED",
            "status": "ACTIVE"
        }
    ]

    cursor = conn.cursor()
    for u in initial_users:
        p_hash, salt = hash_password(dev_password)
        cursor.execute("""
            INSERT INTO users (
                id, auth_user_id, employee_id, username, email,
                password_hash, salt, display_name, department,
                job_title, role, clearance_level, status,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO NOTHING
        """, (
            u["id"], u["auth_user_id"], u["employee_id"], u["username"], u["email"],
            p_hash, salt, u["display_name"], u["department"],
            u["job_title"], u["role"], u["clearance_level"], u["status"],
            now, now
        ))
    conn.commit()


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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
# Initialization Hook: Run ONLY after all functions are defined
# ──────────────────────────────────────────────────────────────────────────────
init_db()
