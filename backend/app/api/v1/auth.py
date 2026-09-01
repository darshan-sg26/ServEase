from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token
from app.models.domain import User, WorkerProfile, ProviderProfile, UserRole, AvailabilityStatus, VerificationStatus
from app.schemas.domain import UserRegister, UserLogin, Token, UserResponse, ProviderProfileResponse

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

@router.post("/register", response_model=Token)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    # Check existing user
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=data.email,
        phone=data.phone,
        password_hash=get_password_hash(data.password),
        role=data.role,
        is_verified=True if data.role == UserRole.ADMIN else False
    )
    db.add(user)
    await db.flush()

    if data.role == UserRole.WORKER:
        w_profile = WorkerProfile(
            user_id=user.id,
            full_name=data.full_name,
            gender=data.gender or "prefer_not_to_say",
            phone=data.phone,
            latitude=data.latitude or 12.9716,
            longitude=data.longitude or 77.5946,
            service_radius_km=15.0,
            availability_status=AvailabilityStatus.AVAILABLE,
            trust_score=30.5,
            verification_status=VerificationStatus.UNVERIFIED
        )
        db.add(w_profile)
        await db.flush()
        from app.services.trust_engine import compute_and_update_trust_score
        await compute_and_update_trust_score(w_profile.id, db)
    elif data.role == UserRole.PROVIDER:
        p_profile = ProviderProfile(
            user_id=user.id,
            full_name=data.full_name,
            phone=data.phone,
            default_latitude=data.latitude or 12.9716,
            default_longitude=data.longitude or 77.5946
        )
        db.add(p_profile)

    await db.commit()

    access_token = create_access_token(subject=user.id, role=user.role.value)
    return Token(access_token=access_token, token_type="bearer", role=user.role.value, user_id=user.id)

@router.post("/login", response_model=Token)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
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
