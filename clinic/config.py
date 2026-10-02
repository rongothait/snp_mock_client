"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatabaseConfig:
    host: str = "db.clinic.internal.example"
    port: int = 5432
    name: str = "clinic"
    user: str = "clinic_app"
    password: str | None = field(default=None, repr=False)
    sslmode: str = "require"

    @classmethod
    def from_env(cls) -> DatabaseConfig:
        return cls(
            host=os.environ.get("CLINIC_DB_HOST", cls.host),
            port=int(os.environ.get("CLINIC_DB_PORT", cls.port)),
            name=os.environ.get("CLINIC_DB_NAME", cls.name),
            user=os.environ.get("CLINIC_DB_USER", cls.user),
            password=os.environ.get("CLINIC_DB_PASSWORD"),
            sslmode=os.environ.get("CLINIC_DB_SSLMODE", cls.sslmode),
        )

    def dsn(self) -> str:
        """libpq-style DSN without the password; the password is passed separately."""
        return (
            f"host={self.host} port={self.port} dbname={self.name} "
            f"user={self.user} sslmode={self.sslmode}"
        )


def _key_from_env(var: str) -> bytes:
    value = os.environ.get(var)
    if value:
        return bytes.fromhex(value)
    logger.warning("%s not set; using an ephemeral key (mock/dev only)", var)
    return secrets.token_bytes(32)


@dataclass(frozen=True)
class AppConfig:
    db: DatabaseConfig
    field_key: bytes = field(repr=False)
    pseudonym_key: bytes = field(repr=False)

    @classmethod
    def from_env(cls) -> AppConfig:
        return cls(
            db=DatabaseConfig.from_env(),
            field_key=_key_from_env("CLINIC_FIELD_KEY"),
            pseudonym_key=_key_from_env("CLINIC_PSEUDONYM_KEY"),
        )
