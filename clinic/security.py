"""Access control, field-level encryption, and pseudonymization.

`FieldCipher` is a stdlib-only stand-in for a real AEAD (e.g. AES-GCM via a KMS);
it has the same shape (nonce + ciphertext + tag) but is not production crypto.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from enum import Enum


class Role(Enum):
    ADMIN = "admin"
    PHYSICIAN = "physician"
    NURSE = "nurse"
    FRONT_DESK = "front_desk"
    BILLING = "billing"
    ANALYST = "analyst"


class Permission(Enum):
    READ_DEMOGRAPHICS = "read_demographics"
    WRITE_DEMOGRAPHICS = "write_demographics"
    READ_CLINICAL = "read_clinical"
    WRITE_CLINICAL = "write_clinical"
    READ_SSN = "read_ssn"
    READ_INSURANCE = "read_insurance"
    MANAGE_SCHEDULE = "manage_schedule"
    RUN_DEIDENTIFIED_REPORTS = "run_deidentified_reports"


# Minimum necessary: each role gets only what its job requires.
ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMIN: frozenset({Permission.READ_DEMOGRAPHICS, Permission.WRITE_DEMOGRAPHICS}),
    Role.PHYSICIAN: frozenset({
        Permission.READ_DEMOGRAPHICS,
        Permission.READ_CLINICAL,
        Permission.WRITE_CLINICAL,
        Permission.MANAGE_SCHEDULE,
    }),
    Role.NURSE: frozenset({
        Permission.READ_DEMOGRAPHICS,
        Permission.READ_CLINICAL,
        Permission.WRITE_CLINICAL,
    }),
    Role.FRONT_DESK: frozenset({
        Permission.READ_DEMOGRAPHICS,
        Permission.WRITE_DEMOGRAPHICS,
        Permission.MANAGE_SCHEDULE,
    }),
    Role.BILLING: frozenset({
        Permission.READ_DEMOGRAPHICS,
        Permission.READ_INSURANCE,
        Permission.READ_SSN,
    }),
    Role.ANALYST: frozenset({Permission.RUN_DEIDENTIFIED_REPORTS}),
}


class AccessDenied(Exception):
    pass


@dataclass(frozen=True)
class Actor:
    """An authenticated staff member."""

    user_id: str
    role: Role

    def can(self, permission: Permission) -> bool:
        return permission in ROLE_PERMISSIONS[self.role]


def require(actor: Actor, permission: Permission) -> None:
    if not actor.can(permission):
        raise AccessDenied(
            f"user_id={actor.user_id} role={actor.role.value} lacks {permission.value}"
        )


class FieldCipher:
    _NONCE_LEN = 16
    _TAG_LEN = 32

    def __init__(self, key: bytes) -> None:
        if len(key) < 32:
            raise ValueError("field key must be at least 32 bytes")
        self._enc_key = hmac.new(key, b"enc", hashlib.sha256).digest()
        self._mac_key = hmac.new(key, b"mac", hashlib.sha256).digest()

    def _keystream(self, nonce: bytes, length: int) -> bytes:
        out = bytearray()
        counter = 0
        while len(out) < length:
            block = counter.to_bytes(8, "big")
            out += hmac.new(self._enc_key, nonce + block, hashlib.sha256).digest()
            counter += 1
        return bytes(out[:length])

    def encrypt(self, plaintext: str) -> bytes:
        data = plaintext.encode()
        nonce = secrets.token_bytes(self._NONCE_LEN)
        body = bytes(a ^ b for a, b in zip(data, self._keystream(nonce, len(data))))
        tag = hmac.new(self._mac_key, nonce + body, hashlib.sha256).digest()
        return nonce + body + tag

    def decrypt(self, blob: bytes) -> str:
        nonce = blob[: self._NONCE_LEN]
        body = blob[self._NONCE_LEN : -self._TAG_LEN]
        tag = blob[-self._TAG_LEN :]
        expected = hmac.new(self._mac_key, nonce + body, hashlib.sha256).digest()
        if not hmac.compare_digest(tag, expected):
            raise ValueError("ciphertext failed integrity check")
        return bytes(a ^ b for a, b in zip(body, self._keystream(nonce, len(body)))).decode()


def pseudonymize(patient_id: str, key: bytes) -> str:
    """Stable, non-reversible identifier for de-identified datasets."""
    return hmac.new(key, patient_id.encode(), hashlib.sha256).hexdigest()[:16]
