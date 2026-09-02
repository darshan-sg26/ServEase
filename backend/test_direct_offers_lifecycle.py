import asyncio
import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token
from app.models.domain import User, UserRole, WorkerProfile, ProviderProfile, DirectOffer, DirectOfferStatus, Job, JobStatus
from sqlalchemy.future import select

async def run_direct_offer_tests():
    print("=" * 70)
    print("Direct Offer Lifecycle & Idempotency Test Suite")
    print("=" * 70)

    async with AsyncSessionLocal() as db:
        w1_user = (await db.execute(select(User).where(User.role == UserRole.WORKER))).scalars().first()
        w1_prof = (await db.execute(select(WorkerProfile).where(WorkerProfile.user_id == w1_user.id))).scalars().first()
        
        # Second worker for auth test
        w2_user = (await db.execute(select(User).where((User.role == UserRole.WORKER) & (User.id != w1_user.id)))).scalars().first()
        
        p_user = (await db.execute(select(User).where(User.role == UserRole.PROVIDER))).scalars().first()
        p_prof = (await db.execute(select(ProviderProfile).where(ProviderProfile.user_id == p_user.id))).scalars().first()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        w1_token = create_access_token(str(w1_user.id), "worker")
        w2_token = create_access_token(str(w2_user.id), "worker") if w2_user else None
        p_token = create_access_token(str(p_user.id), "provider")

        w1_headers = {"Authorization": f"Bearer {w1_token}"}
        w2_headers = {"Authorization": f"Bearer {w2_token}"} if w2_token else None
        p_headers = {"Authorization": f"Bearer {p_token}"}

        print("\n--- 1. Create a Test Direct Offer ---")
        create_res = await client.post(
            "/api/v1/direct-offers",
            json={
                "worker_id": w1_prof.id,
                "title": "Fix Kitchen Sink Pipe Leak",
                "description": "Urgent plumbing repair needed under kitchen sink.",
                "required_skill": "Plumbing",
                "proposed_budget": 500.0,
                "latitude": 12.9716,
                "longitude": 77.5946,
                "scheduled_date": "Today, 4:00 PM"
            },
            headers=p_headers
        )
        assert create_res.status_code == 200, f"Create offer failed: {create_res.text}"
        offer_data = create_res.json()
        offer_id = offer_data["id"]
        assert offer_data["status"] == "pending"
        print(f"[PASS] Offer created with ID #{offer_id}, status: {offer_data['status']}")

        if w2_headers:
            print("\n--- 2. Unauthorized Worker Response Attempt ---")
            unauth_res = await client.patch(
                f"/api/v1/direct-offers/{offer_id}",
                json={"action": "accept"},
                headers=w2_headers
            )
            assert unauth_res.status_code == 403, f"Expected 403, got {unauth_res.status_code}"
            print("[PASS] Unauthorized worker blocked with HTTP 403.")

        print("\n--- 3. Authorized Worker Accepts Direct Offer ---")
        accept_res = await client.patch(
            f"/api/v1/direct-offers/{offer_id}",
            json={"action": "accept"},
            headers=w1_headers
        )
        assert accept_res.status_code == 200, f"Accept failed: {accept_res.text}"
        accepted_data = accept_res.json()
        assert accepted_data["status"] == "accepted"
        assert accepted_data["job_id"] is not None
        job_id = accepted_data["job_id"]
        print(f"[PASS] Offer #{offer_id} accepted -> status: ACCEPTED, created linked Job #{job_id}")

        print("\n--- 4. Verify Linked Job Properties ---")
        job_res = await client.get(f"/api/v1/jobs/{job_id}", headers=w1_headers)
        assert job_res.status_code == 200
        job_info = job_res.json()
        assert job_info["worker_id"] == w1_prof.id
        assert job_info["source"] == "direct_offer"
        assert job_info["status"] == "assigned"
        print(f"[PASS] Linked Job #{job_id} is assigned to Worker #{w1_prof.id} with status: ASSIGNED")

        print("\n--- 5. Idempotent Repeated Acceptance ---")
        repeat_res = await client.patch(
            f"/api/v1/direct-offers/{offer_id}",
            json={"action": "accept"},
            headers=w1_headers
        )
        assert repeat_res.status_code == 200
        repeat_data = repeat_res.json()
        assert repeat_data["status"] == "accepted"
        assert repeat_data["job_id"] == job_id, "Repeated accept must not generate a new job ID!"
        print(f"[PASS] Repeated accept call returned same Job #{repeat_data['job_id']} without duplicate job creation.")

        print("\n--- 6. Attempt to Decline an Already Accepted Offer ---")
        decline_res = await client.patch(
            f"/api/v1/direct-offers/{offer_id}",
            json={"action": "decline"},
            headers=w1_headers
        )
        assert decline_res.status_code == 400
        print(f"[PASS] Blocked declining an already accepted offer: {decline_res.json()['detail']}")

        print("\n--- 7. Create Another Offer & Test Decline State Flow ---")
        create_res2 = await client.post(
            "/api/v1/direct-offers",
            json={
                "worker_id": w1_prof.id,
                "title": "Paint Bedroom Walls",
                "description": "2 coats required",
                "required_skill": "Painting",
                "proposed_budget": 1200.0
            },
            headers=p_headers
        )
        offer2_id = create_res2.json()["id"]

        dec_res2 = await client.patch(
            f"/api/v1/direct-offers/{offer2_id}",
            json={"action": "decline"},
            headers=w1_headers
        )
        assert dec_res2.status_code == 200
        assert dec_res2.json()["status"] == "declined"
        print(f"[PASS] Offer #{offer2_id} transitioned to DECLINED.")

        print("\n--- 8. Attempt to Accept a Declined Offer ---")
        dec_accept_res = await client.patch(
            f"/api/v1/direct-offers/{offer2_id}",
            json={"action": "accept"},
            headers=w1_headers
        )
        assert dec_accept_res.status_code == 400
        print(f"[PASS] Blocked accepting a declined offer: {dec_accept_res.json()['detail']}")

        print("\n--- 9. Complete the Ongoing Job (Dual Confirmation Workflow) ---")
        # Step 1: Worker marks complete
        w_comp = await client.post(f"/api/v1/jobs/{job_id}/complete", headers=w1_headers)
        assert w_comp.status_code == 200
        assert w_comp.json()["worker_completed"] == True
        assert w_comp.json()["status"] == "assigned"
        print("[PASS] Worker confirmed completion -> status remains ASSIGNED waiting for provider.")

        # Step 2: Provider marks complete
        p_comp = await client.post(f"/api/v1/jobs/{job_id}/complete", headers=p_headers)
        assert p_comp.status_code == 200
        assert p_comp.json()["status"] == "completed"
        print(f"[PASS] Provider confirmed completion -> Job #{job_id} transitioned to COMPLETED!")

    print("\n" + "=" * 70)
    print("ALL DIRECT OFFER LIFECYCLE & IDEMPOTENCY TESTS PASSED! ZERO ERRORS.")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_direct_offer_tests())
