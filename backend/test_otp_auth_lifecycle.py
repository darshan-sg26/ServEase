import asyncio
import datetime
import httpx
from unittest.mock import patch
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

    ts = int(datetime.datetime.now().timestamp() * 1000)
    worker_email = f"Test.Worker.{ts}@Gmail.COM"  # Mixed case to test normalization
    provider_email = f"Test.Provider.{ts}@Gmail.COM"
    test_password = "SecurePassword123!"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # ----------------------------------------------------------------------
        # 1. Test Sanitized Error Handling on Email Dispatch Failure
        # ----------------------------------------------------------------------
        print("\n--- 1. Testing Sanitized Error Handling (No Leaked Exceptions) ---")
        with patch("app.api.v1.auth.send_otp_email", side_effect=RuntimeError("Gmail API simulated failure: invalid_grant token expired")):
            fail_res = await ac.post("/api/v1/auth/register", json={
                "email": f"fail.{ts}@gmail.com",
                "password": test_password,
                "full_name": "Fail Test",
                "role": "worker"
            })
            assert fail_res.status_code == 500
            err_detail = fail_res.json()["detail"]
            assert "Unable to send verification email" in err_detail
            assert "invalid_grant" not in err_detail, "Security violation: Raw exception leaked to client!"
            print(f"[PASS] Sanitized error returned without leaking internal details: '{err_detail}'.")

        # ----------------------------------------------------------------------
        # 2. Test Worker Registration with Email Normalization
        # ----------------------------------------------------------------------
        print("\n--- 2. Testing Worker Registration (with mixed case email) ---")
        with patch("app.api.v1.auth.send_otp_email", return_value=True):
            reg_res = await ac.post("/api/v1/auth/register", json={
                "email": worker_email,
                "password": test_password,
                "full_name": "Ramesh Worker",
                "role": "worker",
                "phone": "+919876543299",
                "gender": "male",
                "latitude": 12.9716,
                "longitude": 77.5946
            })
            assert reg_res.status_code == 200, f"Register failed: {reg_res.text}"
            reg_data = reg_res.json()
            assert reg_data["success"] is True
            assert reg_data["requires_verification"] is True
            assert reg_data["email"] == worker_email.strip().lower()
            print(f"[PASS] Register succeeded and normalized email to {reg_data['email']}.")

            # Verify in DB
            norm_worker_email = worker_email.strip().lower()
            async with AsyncSessionLocal() as db:
                pending = (await db.execute(select(PendingRegistration).where(PendingRegistration.email == norm_worker_email))).scalars().first()
                assert pending is not None, "Pending registration was not found in DB!"
                user_check = (await db.execute(select(User).where(User.email == norm_worker_email))).scalars().first()
                assert user_check is None, "Permanent user should NOT be created before OTP verification!"
                print(f"[PASS] Pending registration stored for normalized email: {pending.email}.")

            # ------------------------------------------------------------------
            # 3. Test Duplicate Registration Rejection
            # ------------------------------------------------------------------
            print("\n--- 3. Testing Duplicate Email Rejection ---")
            dup_res = await ac.post("/api/v1/auth/register", json={
                "email": "admin@servease.com",
                "password": "adminpassword123",
                "full_name": "Admin Test",
                "role": "admin"
            })
            assert dup_res.status_code == 400
            print(f"[PASS] Correctly rejected already registered email: {dup_res.json()['detail']}.")

            # ------------------------------------------------------------------
            # 4. Test Incorrect OTP Entry
            # ------------------------------------------------------------------
            print("\n--- 4. Testing Incorrect OTP Entry ---")
            wrong_res = await ac.post("/api/v1/auth/verify-otp", json={
                "email": norm_worker_email,
                "otp": "000000"
            })
            assert wrong_res.status_code == 400
            assert "Incorrect verification code" in wrong_res.json()["detail"]
            print(f"[PASS] Incorrect OTP rejected: {wrong_res.json()['detail']}.")

            # ------------------------------------------------------------------
            # 5. Test Resend Cooldown & Resend Dispatch
            # ------------------------------------------------------------------
            print("\n--- 5. Testing Resend Cooldown Throttling & Dispatch ---")
            cooldown_res = await ac.post("/api/v1/auth/resend-otp", json={"email": norm_worker_email})
            assert cooldown_res.status_code == 429
            print(f"[PASS] Resend cooldown triggered correctly (HTTP 429): {cooldown_res.json()['detail']}.")

            # Fast forward cooldown
            async with AsyncSessionLocal() as db:
                pending = (await db.execute(select(PendingRegistration).where(PendingRegistration.email == norm_worker_email))).scalars().first()
                pending.last_resend_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(seconds=70)
                await db.commit()

            resend_res = await ac.post("/api/v1/auth/resend-otp", json={"email": norm_worker_email})
            assert resend_res.status_code == 200
            print(f"[PASS] Resend OTP succeeded: {resend_res.json()['message']}.")

            # ------------------------------------------------------------------
            # 6. Test Worker OTP Verification & Profile Creation
            # ------------------------------------------------------------------
            print("\n--- 6. Testing Worker OTP Verification & Profile Creation ---")
            known_worker_otp = "123456"
            async with AsyncSessionLocal() as db:
                pending = (await db.execute(select(PendingRegistration).where(PendingRegistration.email == norm_worker_email))).scalars().first()
                pending.otp_hash = hash_otp(known_worker_otp)
                await db.commit()

            # Verify with lowercase email
            verify_res = await ac.post("/api/v1/auth/verify-otp", json={
                "email": norm_worker_email,
                "otp": known_worker_otp
            })
            assert verify_res.status_code == 200
            w_data = verify_res.json()
            assert w_data["role"] == "worker"
            w_user_id = w_data["user_id"]
            print(f"[PASS] Worker verified! User #{w_user_id}, role: {w_data['role']}.")

            # Verify WorkerProfile in DB
            async with AsyncSessionLocal() as db:
                wp = (await db.execute(select(WorkerProfile).where(WorkerProfile.user_id == w_user_id))).scalars().first()
                assert wp is not None, "WorkerProfile was not created!"
                assert wp.full_name == "Ramesh Worker"
                print(f"[PASS] WorkerProfile confirmed in DB: '{wp.full_name}'.")

            # ------------------------------------------------------------------
            # 7. Test Worker Normal Password Login
            # ------------------------------------------------------------------
            print("\n--- 7. Testing Worker Normal Password Login ---")
            login_res = await ac.post("/api/v1/auth/login", json={
                "email": worker_email,  # Test with mixed case email
                "password": test_password
            })
            assert login_res.status_code == 200
            assert login_res.json()["user_id"] == w_user_id
            print(f"[PASS] Worker successfully logged in with password!")

            # ------------------------------------------------------------------
            # 8. Test Provider Registration Flow
            # ------------------------------------------------------------------
            print("\n--- 8. Testing Provider Registration Flow ---")
            p_reg = await ac.post("/api/v1/auth/register", json={
                "email": provider_email,
                "password": test_password,
                "full_name": "Priya Provider",
                "role": "provider"
            })
            assert p_reg.status_code == 200
            norm_provider_email = provider_email.strip().lower()

            known_provider_otp = "654321"
            async with AsyncSessionLocal() as db:
                p_pending = (await db.execute(select(PendingRegistration).where(PendingRegistration.email == norm_provider_email))).scalars().first()
                p_pending.otp_hash = hash_otp(known_provider_otp)
                await db.commit()

            p_verify = await ac.post("/api/v1/auth/verify-otp", json={
                "email": norm_provider_email,
                "otp": known_provider_otp
            })
            assert p_verify.status_code == 200
            p_data = p_verify.json()
            assert p_data["role"] == "provider"
            p_user_id = p_data["user_id"]
            print(f"[PASS] Provider verified! User #{p_user_id}, role: {p_data['role']}.")

            # Verify ProviderProfile in DB
            async with AsyncSessionLocal() as db:
                pp = (await db.execute(select(ProviderProfile).where(ProviderProfile.user_id == p_user_id))).scalars().first()
                assert pp is not None, "ProviderProfile was not created!"
                assert pp.full_name == "Priya Provider"
                print(f"[PASS] ProviderProfile confirmed in DB: '{pp.full_name}'.")

            # ------------------------------------------------------------------
            # 9. Test Provider Normal Password Login
            # ------------------------------------------------------------------
            print("\n--- 9. Testing Provider Normal Password Login ---")
            p_login = await ac.post("/api/v1/auth/login", json={
                "email": provider_email,
                "password": test_password
            })
            assert p_login.status_code == 200
            assert p_login.json()["user_id"] == p_user_id
            print(f"[PASS] Provider successfully logged in with password!")

    print("\n" + "=" * 70)
    print("ALL 9 EMAIL OTP AUTHENTICATION LIFECYCLE TESTS PASSED! ZERO ERRORS.")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_otp_auth_lifecycle())
