import asyncio
import datetime
import httpx
from sqlalchemy.future import select
from app.core.database import AsyncSessionLocal, init_db
from app.models.domain import User, WorkerProfile, ProviderProfile, PendingRegistration, UserRole
from app.services.otp_service import generate_secure_otp, hash_otp, verify_otp_hash
from app.main import app

async def test_otp_auth_lifecycle():
    print("=" * 70)
    print("ServEase Email OTP Registration & Authentication Lifecycle Test Suite")
    print("=" * 70)

    await init_db()

    test_email = f"test.worker.{int(datetime.datetime.now().timestamp() * 1000)}@gmail.com"
    test_password = "SecurePassword123!"
    test_name = "Abhishek Sharma"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # ----------------------------------------------------------------------
        # 1. Test Registration Request
        # ----------------------------------------------------------------------
        print("\n--- 1. Testing Registration Request ---")
        reg_payload = {
            "email": test_email,
            "password": test_password,
            "full_name": test_name,
            "role": "worker",
            "phone": "+919876543299",
            "gender": "male",
            "latitude": 12.9716,
            "longitude": 77.5946
        }
        res = await ac.post("/api/v1/auth/register", json=reg_payload)
        assert res.status_code == 200, f"Register failed: {res.text}"
        data = res.json()
        assert data["success"] is True
        assert data["requires_verification"] is True
        assert "otp" not in data, "Security violation: Plaintext OTP must never be returned in API response!"
        print(f"[PASS] Register returned requires_verification=True for {test_email}.")

        # Verify PendingRegistration created in DB and NOT in permanent users table
        async with AsyncSessionLocal() as db:
            pending = (await db.execute(select(PendingRegistration).where(PendingRegistration.email == test_email))).scalars().first()
            assert pending is not None, "Pending registration was not created in DB!"
            user_check = (await db.execute(select(User).where(User.email == test_email))).scalars().first()
            assert user_check is None, "Permanent user account should NOT be created before OTP verification!"
            stored_otp_hash = pending.otp_hash
            print(f"[PASS] Pending registration stored with secure hash: {stored_otp_hash[:16]}... (Permanent user is NOT yet created).")

        # ----------------------------------------------------------------------
        # 2. Test Duplicate Registration Attempt
        # ----------------------------------------------------------------------
        print("\n--- 2. Testing Existing Email Registration Rejection ---")
        # Attempt registering an existing user email (e.g. admin@servease.com)
        dup_res = await ac.post("/api/v1/auth/register", json={
            "email": "admin@servease.com",
            "password": "adminpassword123",
            "full_name": "Admin Test",
            "role": "admin"
        })
        assert dup_res.status_code == 400, "Should reject already registered email"
        print(f"[PASS] Correctly rejected duplicate registered email: {dup_res.json()['detail']}.")

        # ----------------------------------------------------------------------
        # 3. Test Incorrect OTP Entry
        # ----------------------------------------------------------------------
        print("\n--- 3. Testing Incorrect OTP Entry ---")
        wrong_res = await ac.post("/api/v1/auth/verify-otp", json={
            "email": test_email,
            "otp": "000000"
        })
        assert wrong_res.status_code == 400, "Should reject invalid OTP"
        assert "Incorrect verification code" in wrong_res.json()["detail"]
        print(f"[PASS] Incorrect OTP rejected: {wrong_res.json()['detail']}.")

        # ----------------------------------------------------------------------
        # 4. Test Resend Cooldown (60s Throttling)
        # ----------------------------------------------------------------------
        print("\n--- 4. Testing Resend Cooldown Throttling ---")
        cooldown_res = await ac.post("/api/v1/auth/resend-otp", json={"email": test_email})
        assert cooldown_res.status_code == 429, f"Expected 429 cooldown, got: {cooldown_res.status_code}"
        assert "Please wait" in cooldown_res.json()["detail"]
        print(f"[PASS] Resend cooldown triggered correctly (HTTP 429): {cooldown_res.json()['detail']}.")

        # ----------------------------------------------------------------------
        # 5. Test Resend after Cooldown Expiry
        # ----------------------------------------------------------------------
        print("\n--- 5. Testing Resend OTP after Cooldown ---")
        # Fast-forward last_resend_at by 70 seconds
        async with AsyncSessionLocal() as db:
            pending = (await db.execute(select(PendingRegistration).where(PendingRegistration.email == test_email))).scalars().first()
            pending.last_resend_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(seconds=70)
            await db.commit()

        valid_resend_res = await ac.post("/api/v1/auth/resend-otp", json={"email": test_email})
        assert valid_resend_res.status_code == 200, f"Resend failed: {valid_resend_res.text}"
        print(f"[PASS] Resend OTP succeeded: {valid_resend_res.json()['message']}.")

        # ----------------------------------------------------------------------
        # 6. Test Successful OTP Verification & Account Creation
        # ----------------------------------------------------------------------
        print("\n--- 6. Testing Successful OTP Verification ---")
        # Retrieve the newly generated OTP from memory hash test or simulate with known OTP
        known_otp = "852963"
        async with AsyncSessionLocal() as db:
            pending = (await db.execute(select(PendingRegistration).where(PendingRegistration.email == test_email))).scalars().first()
            pending.otp_hash = hash_otp(known_otp)
            await db.commit()

        verify_res = await ac.post("/api/v1/auth/verify-otp", json={
            "email": test_email,
            "otp": known_otp
        })
        assert verify_res.status_code == 200, f"Verification failed: {verify_res.text}"
        auth_data = verify_res.json()
        assert "access_token" in auth_data
        assert auth_data["role"] == "worker"
        user_id = auth_data["user_id"]
        print(f"[PASS] Verification successful! Received JWT access token for User #{user_id}.")

        # Verify in DB: Pending registration cleaned up, permanent user created
        async with AsyncSessionLocal() as db:
            pending = (await db.execute(select(PendingRegistration).where(PendingRegistration.email == test_email))).scalars().first()
            assert pending is None, "Pending registration was not deleted after successful verification!"
            created_user = (await db.execute(select(User).where(User.id == user_id))).scalars().first()
            assert created_user is not None, "Permanent user was not found in DB!"
            assert created_user.is_verified is True
            worker_prof = (await db.execute(select(WorkerProfile).where(WorkerProfile.user_id == user_id))).scalars().first()
            assert worker_prof is not None, "Worker profile was not created!"
            print(f"[PASS] Permanent User and WorkerProfile verified in DB (Pending record cleanly purged).")

        # ----------------------------------------------------------------------
        # 7. Test Login with Newly Created Credentials
        # ----------------------------------------------------------------------
        print("\n--- 7. Testing Login with Newly Created Account ---")
        login_res = await ac.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        login_data = login_res.json()
        assert login_data["user_id"] == user_id
        print(f"[PASS] Login successful with verified credentials.")

    print("\n" + "=" * 70)
    print("ALL EMAIL OTP AUTHENTICATION LIFECYCLE TESTS PASSED! ZERO ERRORS.")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_otp_auth_lifecycle())
