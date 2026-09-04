import hashlib
import hmac
import secrets
from app.core.config import settings

def generate_secure_otp() -> str:
    """
    Generates a cryptographically random 6-digit numeric OTP (100000 - 999999).
    """
    # secrets.randbelow is cryptographically secure (uses os.urandom under the hood)
    code = secrets.randbelow(900000) + 100000
    return str(code)

def hash_otp(otp: str) -> str:
    """
    Produces a secure SHA-256 digest of the OTP combined with the application secret key as pepper.
    """
    salted = f"{otp}:{settings.SECRET_KEY}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()

def verify_otp_hash(plain_otp: str, hashed_otp: str) -> bool:
    """
    Constant-time verification of a candidate plaintext OTP against the stored hash.
    """
    if not plain_otp or not hashed_otp:
        return False
    computed_hash = hash_otp(plain_otp.strip())
    return hmac.compare_digest(computed_hash, hashed_otp.strip())
