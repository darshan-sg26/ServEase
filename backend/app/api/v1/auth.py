import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token
from app.models.domain import (
    User, WorkerProfile, ProviderProfile, UserRole, AvailabilityStatus, VerificationStatus, PendingRegistration
)
from app.schemas.domain import (
    UserRegister, UserRegisterResponse, VerifyOtpRequest, ResendOtpRequest, SimpleResponse,
    UserLogin, Token, UserResponse, ProviderProfileResponse
)
from app.services.otp_service import generate_secure_otp, hash_otp, verify_otp_hash
from app.services.email_service import send_otp_email

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/register", response_model=UserRegisterResponse)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    """
    Step 1 of Registration: Validates input, hashes password, saves pending registration,
    and sends a 6-digit verification OTP to the user's email via Gmail SMTP.
    """
    # 1. Check if email is already registered in permanent users table
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="An account with this email already exists. Please sign in.")

    # 2. Validate password length
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")

    # 3. Generate cryptographically secure OTP & Hash
    plain_otp = generate_secure_otp()
    otp_digest = hash_otp(plain_otp)
    expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

    # 4. Hash user password securely with bcrypt before staging
    pwd_hash = get_password_hash(data.password)
    staged_payload = {
        "email": data.email,
        "password_hash": pwd_hash,
        "role": data.role.value,
        "full_name": data.full_name,
        "phone": data.phone or "+919876543210",
        "gender": data.gender or "prefer_not_to_say",
        "latitude": data.latitude or 12.9716,
        "longitude": data.longitude or 77.5946,
    }

    # 5. Check if pending registration already exists for this email
    pending_res = await db.execute(select(PendingRegistration).where(PendingRegistration.email == data.email))
    pending = pending_res.scalars().first()

    if pending:
        pending.otp_hash = otp_digest
        pending.otp_expires_at = expiry
        pending.registration_data = staged_payload
        pending.attempts = 0
        pending.last_resend_at = datetime.datetime.utcnow()
    else:
        pending = PendingRegistration(
            email=data.email,
            otp_hash=otp_digest,
            otp_expires_at=expiry,
            registration_data=staged_payload,
            attempts=0,
            last_resend_at=datetime.datetime.utcnow()
        )
        db.add(pending)

    # 6. Send OTP Email via Gmail SMTP
    try:
        await send_otp_email(
            to_email=data.email,
            otp=plain_otp,
            recipient_name=data.full_name
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send verification email: {str(e)}"
        )

    await db.commit()

    return UserRegisterResponse(
        success=True,
        message=f"Verification code sent to {data.email}",
        requires_verification=True,
        email=data.email
    )

@router.post("/verify-otp", response_model=Token)
async def verify_otp(data: VerifyOtpRequest, db: AsyncSession = Depends(get_db)):
    """
    Step 2 of Registration: Verifies the 6-digit OTP against pending registration,
    creates the permanent User & Profile in the database, cleans up pending data,
    and returns an authenticated JWT session.
    """
    # 1. Fetch pending registration
    pending_res = await db.execute(select(PendingRegistration).where(PendingRegistration.email == data.email))
    pending = pending_res.scalars().first()

    if not pending:
        raise HTTPException(status_code=404, detail="No pending registration found for this email. Please register again.")

    # 2. Check maximum attempts
    if pending.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many incorrect attempts. Please request a new verification code."
        )

    # 3. Check expiration
    if datetime.datetime.utcnow() > pending.otp_expires_at:
        raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new code.")

    # 4. Verify OTP Constant-Time Hash
    if not verify_otp_hash(data.otp, pending.otp_hash):
        pending.attempts += 1
        await db.commit()
        remaining = settings.OTP_MAX_ATTEMPTS - pending.attempts
        if remaining > 0:
            raise HTTPException(status_code=400, detail=f"Incorrect verification code. {remaining} attempt(s) remaining.")
        else:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many incorrect attempts. Please request a new code.")

    # 5. OTP is valid -> Create permanent user account
    reg = pending.registration_data
    role = UserRole(reg["role"])

    # Double check email availability
    existing_user_res = await db.execute(select(User).where(User.email == data.email))
    if existing_user_res.scalars().first():
        await db.delete(pending)
        await db.commit()
        raise HTTPException(status_code=400, detail="Account is already registered. Please sign in.")

    user = User(
        email=reg["email"],
        phone=reg.get("phone"),
        password_hash=reg["password_hash"],
        role=role,
        is_verified=True
    )
    db.add(user)
    await db.flush()

    if role == UserRole.WORKER:
        w_profile = WorkerProfile(
            user_id=user.id,
            full_name=reg.get("full_name", ""),
            gender=reg.get("gender") or "prefer_not_to_say",
            phone=reg.get("phone"),
            latitude=reg.get("latitude") or 12.9716,
            longitude=reg.get("longitude") or 77.5946,
            service_radius_km=15.0,
            availability_status=AvailabilityStatus.AVAILABLE,
            trust_score=30.5,
            verification_status=VerificationStatus.VERIFIED
        )
        db.add(w_profile)
        await db.flush()
        from app.services.trust_engine import compute_and_update_trust_score
        await compute_and_update_trust_score(w_profile.id, db)
    elif role == UserRole.PROVIDER:
        p_profile = ProviderProfile(
            user_id=user.id,
            full_name=reg.get("full_name", ""),
            phone=reg.get("phone"),
            default_latitude=reg.get("latitude") or 12.9716,
            default_longitude=reg.get("longitude") or 77.5946
        )
        db.add(p_profile)

    # Clean up pending registration
    await db.delete(pending)
    await db.commit()

    # Generate JWT session token
    access_token = create_access_token(subject=user.id, role=user.role.value)
    return Token(access_token=access_token, token_type="bearer", role=user.role.value, user_id=user.id)

@router.post("/resend-otp", response_model=SimpleResponse)
async def resend_otp(data: ResendOtpRequest, db: AsyncSession = Depends(get_db)):
    """
    Resends a new 6-digit OTP code to the pending user's email, enforcing a 60-second cooldown.
    """
    pending_res = await db.execute(select(PendingRegistration).where(PendingRegistration.email == data.email))
    pending = pending_res.scalars().first()

    if not pending:
        raise HTTPException(status_code=404, detail="No pending registration found for this email. Please register again.")

    # Check 60-second cooldown
    now = datetime.datetime.utcnow()
    elapsed = (now - pending.last_resend_at).total_seconds()
    if elapsed < settings.OTP_RESEND_COOLDOWN_SECONDS:
        remaining = int(settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Please wait {remaining} second(s) before requesting a new code."
        )

    # Generate new OTP & invalidate previous
    plain_otp = generate_secure_otp()
    pending.otp_hash = hash_otp(plain_otp)
    pending.otp_expires_at = now + datetime.timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    pending.attempts = 0
    pending.last_resend_at = now

    # Dispatch email
    recipient_name = pending.registration_data.get("full_name", "")
    try:
        await send_otp_email(to_email=data.email, otp=plain_otp, recipient_name=recipient_name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send verification email: {str(e)}"
        )

    await db.commit()

    return SimpleResponse(
        success=True,
        message=f"A fresh verification code has been sent to {data.email}."
    )

@router.post("/login", response_model=Token)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Authenticates an existing verified user with email and password.
    """
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalars().first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    access_token = create_access_token(subject=user.id, role=user.role.value)
    return Token(access_token=access_token, token_type="bearer", role=user.role.value, user_id=user.id)

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/providers/me", response_model=ProviderProfileResponse)
async def get_my_provider_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from app.services.rating_service import build_provider_profile_response
    result = await db.execute(select(ProviderProfile).where(ProviderProfile.user_id == current_user.id))
    provider = result.scalars().first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found")
    return await build_provider_profile_response(provider, db)
