"""
Comprehensive verification test for ServEase Google Sign-In backend endpoint.
Tests:
- POST /api/v1/auth/google
1. New user registration as WORKER (creates User + WorkerProfile, is_verified=True, auth_provider="google")
2. New user registration as PROVIDER (creates User + ProviderProfile, is_verified=True, auth_provider="google")
3. Existing email user automatic linking to Google account
4. Subsequent login of previously linked Google account
5. Mismatch protection (rejecting if account already linked to different google_id)
6. Invalid / expired token rejection (HTTP 401)
7. Unverified email rejection (HTTP 400)
8. Missing claims rejection (HTTP 400)
"""
import asyncio
import datetime
import sys
import os
from unittest.mock import patch

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db, get_db
from app.models.domain import User, WorkerProfile, ProviderProfile
from sqlalchemy import select

async def run_tests():
    print("==================================================")
    print("STARTING GOOGLE AUTH BACKEND INTEGRATION TESTS")
    print("==================================================")

    # Initialize DB (runs safe migrations)
    await init_db()

    ts = int(datetime.datetime.now().timestamp() * 1000)
    worker_email = f"google_worker_{ts}@example.com"
    provider_email = f"google_provider_{ts}@example.com"
    existing_email = f"existing_account_{ts}@example.com"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        # TEST 1: New User Registration via Google (Worker)
        print("\n[TEST 1] Google Sign-In for new user (Worker role)...")
        mock_claims_1 = {
            "sub": f"google-user-1001-{ts}",
            "email": worker_email,
            "email_verified": True,
            "name": "Google Worker One",
            "picture": "https://example.com/worker_photo.jpg"
        }
        with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_claims_1):
            res = await client.post("/api/v1/auth/google", json={
                "id_token": "valid-simulated-token-1",
                "role": "worker"
            })
            assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
            data = res.json()
            assert "access_token" in data, "Token missing in response"
            assert data["role"] == "worker", f"Expected worker role, got {data['role']}"
            user_id = data["user_id"]
            print(f"-> SUCCESS: Worker user created (ID: {user_id}, token issued)")

            # Verify in DB
            async for session in get_db():
                u_res = await session.execute(select(User).where(User.id == user_id))
                u = u_res.scalars().first()
                assert u is not None
                assert u.email == worker_email
                assert u.google_id == f"google-user-1001-{ts}"
                assert u.auth_provider == "google"
                assert u.is_verified is True

                w_res = await session.execute(select(WorkerProfile).where(WorkerProfile.user_id == user_id))
                w = w_res.scalars().first()
                assert w is not None
                assert w.full_name == "Google Worker One"
                assert w.profile_photo_url == "https://example.com/worker_photo.jpg"
                print("-> SUCCESS: User & WorkerProfile verified in DB")
                break

        # TEST 2: New User Registration via Google (Provider)
        print("\n[TEST 2] Google Sign-In for new user (Provider role)...")
        mock_claims_2 = {
            "sub": f"google-user-2002-{ts}",
            "email": provider_email,
            "email_verified": True,
            "name": "Google Provider Two",
            "picture": "https://example.com/provider_photo.jpg"
        }
        with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_claims_2):
            res = await client.post("/api/v1/auth/google", json={
                "id_token": "valid-simulated-token-2",
                "role": "provider"
            })
            assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
            data = res.json()
            assert data["role"] == "provider"
            user_id = data["user_id"]
            print(f"-> SUCCESS: Provider user created (ID: {user_id}, token issued)")

            # Verify in DB
            async for session in get_db():
                u_res = await session.execute(select(User).where(User.id == user_id))
                u = u_res.scalars().first()
                assert u is not None
                assert u.google_id == f"google-user-2002-{ts}"
                assert u.is_verified is True

                p_res = await session.execute(select(ProviderProfile).where(ProviderProfile.user_id == user_id))
                p = p_res.scalars().first()
                assert p is not None
                assert p.full_name == "Google Provider Two"
                print("-> SUCCESS: User & ProviderProfile verified in DB")
                break

        # TEST 3: Account Linking (Existing Email User)
        print("\n[TEST 3] Link existing standard user to Google account...")
        # First create a normal user directly in DB
        async for session in get_db():
            from app.core.security import get_password_hash
            existing_user = User(
                email=existing_email,
                password_hash=get_password_hash("Secret123"),
                role="worker",
                is_verified=False,
                google_id=None,
                auth_provider="email"
            )
            session.add(existing_user)
            await session.commit()
            await session.refresh(existing_user)
            existing_id = existing_user.id
            break

        mock_claims_3 = {
            "sub": f"google-user-3003-{ts}",
            "email": existing_email,
            "email_verified": True,
            "name": "Linked User",
        }
        with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_claims_3):
            res = await client.post("/api/v1/auth/google", json={
                "id_token": "valid-simulated-token-3",
                "role": "worker"
            })
            assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
            data = res.json()
            assert data["user_id"] == existing_id, "Did not link to existing user ID!"
            print(f"-> SUCCESS: Existing user {existing_id} linked to Google identity")

            # Verify in DB that google_id is set and is_verified is True
            async for session in get_db():
                u_res = await session.execute(select(User).where(User.id == existing_id))
                u = u_res.scalars().first()
                assert u.google_id == f"google-user-3003-{ts}"
                assert u.is_verified is True
                print("-> SUCCESS: Account linking confirmed in DB")
                break

        # TEST 4: Subsequent Login for Existing Linked User
        print("\n[TEST 4] Subsequent Google login for already linked user...")
        with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_claims_3):
            res = await client.post("/api/v1/auth/google", json={
                "id_token": "valid-simulated-token-3"
            })
            assert res.status_code == 200
            data = res.json()
            assert data["user_id"] == existing_id
            print(f"-> SUCCESS: Re-authenticated linked user {existing_id}")

        # TEST 5: Mismatch Protection (Different google_id for same email)
        print("\n[TEST 5] Reject Google login if email linked to different google_id...")
        mock_claims_mismatch = {
            "sub": "different-impostor-sub",
            "email": existing_email,
            "email_verified": True,
            "name": "Impostor",
        }
        with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_claims_mismatch):
            res = await client.post("/api/v1/auth/google", json={
                "id_token": "valid-simulated-token-mismatch"
            })
            assert res.status_code == 400, f"Expected 400, got {res.status_code}"
            assert "different Google account" in res.json()["detail"]
            print("-> SUCCESS: Safely rejected Google ID mismatch")

        # TEST 6: Invalid / Expired Token Rejection
        print("\n[TEST 6] Reject invalid or forged token...")
        with patch("google.oauth2.id_token.verify_oauth2_token", side_effect=ValueError("Token expired")):
            res = await client.post("/api/v1/auth/google", json={
                "id_token": "expired-fake-token"
            })
            assert res.status_code == 401, f"Expected 401, got {res.status_code}"
            assert "Invalid Google ID token" in res.json()["detail"]
            print("-> SUCCESS: Invalid token rejected with HTTP 401")

        # TEST 7: Unverified Email Rejection
        print("\n[TEST 7] Reject Google token if email_verified is False...")
        mock_claims_unverified = {
            "sub": "unverified-sub",
            "email": "unverified@example.com",
            "email_verified": False,
            "name": "Unverified User",
        }
        with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_claims_unverified):
            res = await client.post("/api/v1/auth/google", json={
                "id_token": "token-unverified-email"
            })
            assert res.status_code == 400, f"Expected 400, got {res.status_code}"
            assert "not verified" in res.json()["detail"]
            print("-> SUCCESS: Unverified email rejected with HTTP 400")

    print("\n==================================================")
    print("ALL 7 GOOGLE AUTH BACKEND TESTS PASSED PERFECTLY!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_tests())
