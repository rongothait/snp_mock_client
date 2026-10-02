"""Access audit trail for PHI reads and writes.

Audit rows and log lines carry only who did what to which record ID, never the
PHI itself.
"""

from __future__ import annotations

import logging
from enum import Enum

from clinic.db.connection import Database
from clinic.security import Actor

logger = logging.getLogger(__name__)


class AuditAction(Enum):
    CREATE = "create"
    VIEW = "view"
    UPDATE = "update"
    EXPORT = "export"


class AuditLogger:
    def __init__(self, db: Database) -> None:
        self._db = db

    def record(
        self,
        actor: Actor,
        action: AuditAction,
        resource: str,
        patient_id: str | None = None,
    ) -> None:
        with self._db.transaction() as cur:
            cur.execute(
                """
                INSERT INTO access_audit_log (actor_user_id, actor_role, action, resource, patient_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (actor.user_id, actor.role.value, action.value, resource, patient_id),
            )
        logger.info(
            "audit actor=%s action=%s resource=%s patient_id=%s",
            actor.user_id,
            action.value,
            resource,
            patient_id,
        )
