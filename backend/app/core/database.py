"""
Database Engine & Persistence Layer for SEMANTIQ
Supports SQLite (local development/testing) and PostgreSQL (production deployment).
Manages tables: users, entities, relationships, and change_audit_logs.
Seeds initial benchmark accounts and graph topology safely on initialization.
"""
import sqlite3
import os
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
# Database Connection
# ──────────────────────────────────────────────────────────────────────────────

def get_db_connection():
    """Returns a connection to the SQLite database with Row factory enabled."""
    db_path = settings.DATABASE_PATH
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    return conn


def init_db():
    """Initializes the database schema and seeds initial accounts and graph entities if empty."""
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

        conn.commit()

        # Ensure missing columns exist in users table (migration safety)
        cursor.execute("PRAGMA table_info(users)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        if "username" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
        if "auth_user_id" not in existing_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN auth_user_id TEXT")

        # Ensure missing columns exist in relationships table (migration safety)
        cursor.execute("PRAGMA table_info(relationships)")
        existing_rel_cols = {row[1] for row in cursor.fetchall()}
        if "weight" not in existing_rel_cols:
            cursor.execute("ALTER TABLE relationships ADD COLUMN weight REAL DEFAULT 1.0")
        if "description" not in existing_rel_cols:
            cursor.execute("ALTER TABLE relationships ADD COLUMN description TEXT")

        conn.commit()

        # Update any NULL username or auth_user_id
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


# Auto-initialize database on module import so all standalone test runners have ready tables
init_db()


def _seed_initial_users(conn: sqlite3.Connection):
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
        """, (
            u["id"], u["auth_user_id"], u["employee_id"], u["username"], u["email"],
            p_hash, salt, u["display_name"], u["department"],
            u["job_title"], u["role"], u["clearance_level"], u["status"],
            now, now
        ))
    conn.commit()


def _seed_initial_graph(conn: sqlite3.Connection):
    """Seeds the initial graph entities and relationships from SEED data with ACTIVE and VERIFIED status."""
    from app.data.seed_data import SEED_ENTITIES, SEED_RELATIONSHIPS
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.cursor()

    for ent in SEED_ENTITIES:
        cursor.execute("""
            INSERT OR IGNORE INTO entities (
                id, type, name, description, metadata, access_tier,
                status, owner_team, created_by, created_at, updated_at, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            INSERT OR IGNORE INTO relationships (
                id, source_entity_id, relationship_type, target_entity_id,
                created_by, created_at, status, access_tier, evidence_ids,
                version, reviewed_by, reviewed_at, review_comment, weight, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
