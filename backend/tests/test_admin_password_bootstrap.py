"""
REMOVED: The temporary admin password bootstrap mechanism (ADMIN_BOOTSTRAP_PASSWORD)
has been removed from SEMANTIQ. This file is kept as a placeholder to record that removal.

The bootstrap mechanism was a temporary recovery path. It has been replaced by:
- Deterministic benchmark account seeding via SEED_*_PASSWORD environment variables.
- Standard admin user management via POST /api/admin/users/invite and PATCH endpoints.

No tests in this module are active.
"""
