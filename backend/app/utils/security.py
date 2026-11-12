"""
Security utilities for password hashing (Argon2 / Bcrypt with RFC 7914 Scrypt fallback)
and RFC 7519 JWT token creation and verification.
"""
import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from app.config import settings

# 1. Password Hashing Support (Argon2 -> Bcrypt -> Standard Library Scrypt KDF)
try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError

    _argon2_hasher = PasswordHasher(
        time_cost=2, memory_cost=65536, parallelism=2, hash_len=32, salt_len=16
    )
    HAS_ARGON2 = True
except ImportError:
    _argon2_hasher = None
    HAS_ARGON2 = False

try:
    import bcrypt as _bcrypt

    HAS_BCRYPT = True
except ImportError:
    _bcrypt = None
    HAS_BCRYPT = False

# 2. JWT Library Support (PyJWT -> Standard RFC 7519 HMAC-SHA256 implementation)
try:
    import jwt as _pyjwt

    HAS_PYJWT = True
except ImportError:
    _pyjwt = None
    HAS_PYJWT = False


class InvalidTokenError(Exception):
    """Raised when a JWT token is malformed, tampered with, or expired."""


def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password using Argon2id (preferred), bcrypt, or RFC 7914 scrypt.
    Never stores plaintext passwords.
    """
    if not plain_password:
        raise ValueError("Password cannot be empty.")

    if HAS_ARGON2 and _argon2_hasher is not None and settings.PASSWORD_HASH_SCHEME == "argon2":
        return _argon2_hasher.hash(plain_password)

    if HAS_BCRYPT and _bcrypt is not None:
        salt = _bcrypt.gensalt(rounds=12)
        return _bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")

    # Standard library cryptographic KDF (RFC 7914 scrypt)
    salt_bytes = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        plain_password.encode("utf-8"),
        salt=salt_bytes,
        n=16384,
        r=8,
        p=1,
        dklen=32,
    )
    salt_b64 = base64.b64encode(salt_bytes).decode("ascii")
    dk_b64 = base64.b64encode(derived).decode("ascii")
    return f"$scrypt$n=16384,r=8,p=1${salt_b64}${dk_b64}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored Argon2, bcrypt, or scrypt hash."""
    if not plain_password or not hashed_password:
        return False

    try:
        if hashed_password.startswith("$argon2") and HAS_ARGON2 and _argon2_hasher is not None:
            try:
                return bool(_argon2_hasher.verify(hashed_password, plain_password))
            except VerifyMismatchError:
                return False

        if hashed_password.startswith("$2") and HAS_BCRYPT and _bcrypt is not None:
            return bool(
                _bcrypt.checkpw(
                    plain_password.encode("utf-8"),
                    hashed_password.encode("utf-8"),
                )
            )

        if hashed_password.startswith("$scrypt$"):
            parts = hashed_password.split("$")
            if len(parts) != 5:
                return False
            params_str, salt_b64, expected_b64 = parts[2], parts[3], parts[4]
            params = dict(item.split("=") for item in params_str.split(","))
            salt_bytes = base64.b64decode(salt_b64.encode("ascii"))
            expected_bytes = base64.b64decode(expected_b64.encode("ascii"))
            derived = hashlib.scrypt(
                plain_password.encode("utf-8"),
                salt=salt_bytes,
                n=int(params.get("n", 16384)),
                r=int(params.get("r", 8)),
                p=int(params.get("p", 1)),
                dklen=len(expected_bytes),
            )
            return hmac.compare_digest(derived, expected_bytes)
    except Exception:
        return False

    return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * ((4 - len(segment) % 4) % 4)
    return base64.urlsafe_b64decode((segment + padding).encode("ascii"))


def create_access_token(
    subject: str,
    user_id: int,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token containing user identity and role claims."""
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "user_id": int(user_id),
        "role": str(role),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    if HAS_PYJWT and _pyjwt is not None:
        token = _pyjwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        return token if isinstance(token, str) else token.decode("utf-8")

    # Standard RFC 7519 HS256 JWT encoding
    header = {"alg": settings.JWT_ALGORITHM, "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    sig_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """Verify and decode a JWT access token, raising InvalidTokenError on failure."""
    if not token or not isinstance(token, str):
        raise InvalidTokenError("Missing authentication token.")

    if HAS_PYJWT and _pyjwt is not None:
        try:
            return dict(
                _pyjwt.decode(
                    token,
                    settings.JWT_SECRET_KEY,
                    algorithms=[settings.JWT_ALGORITHM],
                )
            )
        except Exception as exc:
            raise InvalidTokenError(f"Invalid or expired token: {exc}") from exc

    # Standard RFC 7519 HS256 verification
    parts = token.split(".")
    if len(parts) != 3:
        raise InvalidTokenError("Malformed JWT structure.")

    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    try:
        actual_sig = _b64url_decode(sig_b64)
        header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception as exc:
        raise InvalidTokenError("Failed to decode token segments.") from exc

    if header.get("alg") != settings.JWT_ALGORITHM:
        raise InvalidTokenError("Unsupported JWT signing algorithm.")

    if not hmac.compare_digest(actual_sig, expected_sig):
        raise InvalidTokenError("Invalid token signature.")

    exp = payload.get("exp")
    if exp is None or int(exp) < int(time.time()):
        raise InvalidTokenError("Token has expired.")

    return dict(payload)
