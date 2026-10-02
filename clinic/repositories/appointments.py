"""Persistence for appointments."""

from __future__ import annotations

from datetime import date

from clinic.db.connection import Database
from clinic.models import Appointment

_COLUMNS = (
    "appointment_id", "patient_id", "provider_id", "scheduled_at",
    "duration_minutes", "status", "reason",
)


class AppointmentRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def insert(self, appointment: Appointment) -> None:
        with self._db.transaction() as cur:
            cur.execute(
                """
                INSERT INTO appointments (
                    appointment_id, patient_id, provider_id, scheduled_at,
                    duration_minutes, status, reason
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    appointment.appointment_id, appointment.patient_id, appointment.provider_id,
                    appointment.scheduled_at, appointment.duration_minutes,
                    appointment.status, appointment.reason,
                ),
            )

    def update_status(self, appointment_id: str, status: str) -> None:
        with self._db.transaction() as cur:
            cur.execute(
                "UPDATE appointments SET status = %s WHERE appointment_id = %s",
                (status, appointment_id),
            )

    def list_for_provider(self, provider_id: str, day: date) -> list[Appointment]:
        with self._db.transaction() as cur:
            cur.execute(
                f"""
                SELECT {', '.join(_COLUMNS)} FROM appointments
                 WHERE provider_id = %s AND scheduled_at::date = %s
                 ORDER BY scheduled_at
                """,
                (provider_id, day),
            )
            rows = cur.fetchall()
        return [Appointment(**dict(zip(_COLUMNS, row))) for row in rows]
