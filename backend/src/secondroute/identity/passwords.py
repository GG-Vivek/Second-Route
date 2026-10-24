"""
Password hashing for the accounts that sign in to the application.

Passwords are never stored. What is stored is a scrypt hash with its own salt
and its cost parameters, so that the hash can be checked again later even if
the cost is raised for new accounts. The standard library provides scrypt, so
no third-party dependency is added.

The module imports nothing from the rest of the application, so the hashing can
be tested without a database or a web framework.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import secrets
from typing import Final

__all__ = ["hash_password", "verify_password"]

#: The algorithm name written at the front of every stored hash.
ALGORITHM: Final[str] = "scrypt"

#: The cost of a new hash: CPU/memory cost, block size, parallelism.
_N: Final[int] = 2**14
_R: Final[int] = 8
_P: Final[int] = 1
_DKLEN: Final[int] = 32
_SALT_BYTES: Final[int] = 16
_MAX_MEMORY: Final[int] = 64 * 1024 * 1024


def _encode(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _decode(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"), validate=True)


def hash_password(password: str) -> str:
    """Return a hash of a password, ready to be stored.

    Args:
        password: The password as the person typed it.

    Returns:
        A string holding the algorithm, its parameters, the salt and the digest.
    """
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_N,
        r=_R,
        p=_P,
        dklen=_DKLEN,
        maxmem=_MAX_MEMORY,
    )
    return "$".join([ALGORITHM, str(_N), str(_R), str(_P), _encode(salt), _encode(digest)])


def verify_password(password: str, stored: str | None) -> bool:
    """Check a password against a stored hash.

    A malformed or missing hash never matches. The comparison is constant
    time, so the answer does not reveal how much of the digest was right.

    Args:
        password: The password the person typed.
        stored: The hash that was stored for the account, or None.

    Returns:
        True when the password is the one the hash was made from.
    """
    if not stored:
        return False
    parts = stored.split("$")
    if len(parts) != 6 or parts[0] != ALGORITHM:
        return False
    try:
        n, r, p = int(parts[1]), int(parts[2]), int(parts[3])
        salt = _decode(parts[4])
        expected = _decode(parts[5])
    except (ValueError, binascii.Error):
        return False
    if not expected:
        return False
    try:
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=len(expected),
            maxmem=_MAX_MEMORY,
        )
    except ValueError:
        return False
    return hmac.compare_digest(actual, expected)
