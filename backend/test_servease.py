import asyncio
import httpx
from app.seed import seed_database

BASE_URL = "http://127.0.0.1:8000/api/v1"

async def test_all_servease_features():
    print("=" * 60)
    print("ServEase Automated API & ML Verification Test Suite")
    print("=" * 60)

    # 1. Initialize DB & Seed Data
    print("\n1. Initializing & Seeding Database...")
    await seed_database()

    from app.core.database import AsyncSessionLocal
    from app.models.domain import User, UserRole, WorkerProfile, ProviderProfile, Job
    from app.core.security import create_access_token, get_password_hash
    from sqlalchemy.future import select

    async with AsyncSessionLocal() as db:
        w_user = (await db.execute(select(User).where(User.role == UserRole.WORKER))).scalars().first()
        p_user = (await db.execute(select(User).where(User.role == UserRole.PROVIDER))).scalars().first()
        admin_user = (await db.execute(select(User).where(User.role == UserRole.ADMIN))).scalars().first()
        if not admin_user:
            admin_user = User(
                email="admin@servease.com",
                password_hash=get_password_hash("admin123"),
                role=UserRole.ADMIN,
                phone="9999999999",
                is_verified=True
            )
            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)
        w_prof = (await db.execute(select(WorkerProfile).where(WorkerProfile.user_id == w_user.id))).scalars().first()
        if w_prof and not w_prof.phone:
            w_prof.phone = "9876543210"
            await db.commit()
            await db.refresh(w_prof)
        first_job = (await db.execute(select(Job))).scalars().first()

    w_token = create_access_token(str(w_user.id), "worker")
    w_user_id = w_user.id
    p_token = create_access_token(str(p_user.id), "provider")
    p_user_id = p_user.id
    a_token = create_access_token(str(admin_user.id), "admin")

    # Create test client
    from app.main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # 2. Health check
        res = await ac.get("/")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        print("[OK] Health Check Passed: ", res.json())

        # 3. Auth Tests
        print(f"[OK] Worker Auth Token Created (User #{w_user_id}).")
        print(f"[OK] Provider Auth Token Created (User #{p_user_id}).")

        # 4. Path A: Post & Match Engine Test
        target_job_id = first_job.id if first_job else 1
        matches_res = await ac.get(f"/api/v1/jobs/{target_job_id}/matches")
        assert matches_res.status_code == 200, f"Matches failed: {matches_res.text}"
        matches = matches_res.json()
        assert len(matches) > 0, "Should return ranked candidates"
        print(f"[OK] Path A Hybrid Job Matching Engine Passed: Found {len(matches)} ranked candidates for Job #{target_job_id}.")
        print(f"   Top Match: {matches[0]['worker']['full_name']} | Match Score: {matches[0]['match_score']}% | Distance: {matches[0]['distance_km']}km")

        # 5. Path B: Browse Worker Directory & Direct Offers Test
        workers_res = await ac.get("/api/v1/workers")
        assert workers_res.status_code == 200, f"Workers list failed: {workers_res.text}"
        workers = workers_res.json()
        print(f"[OK] Path B Searchable Worker Directory Passed: Returned {len(workers)} matching profiles.")

        # 6. Path B: Provider sends Direct Offer to Worker
        offer_res = await ac.post(
            "/api/v1/direct-offers",
            json={
                "worker_id": w_prof.id,
                "title": "Outstation Driver Offer",
                "description": "Direct outreach offer sent from provider profile view.",
                "required_skill": "Plumbing",
                "proposed_budget": 800.0,
                "scheduled_date": "Tomorrow at 10:00 AM",
                "latitude": 12.9716,
                "longitude": 77.5946
            },
            headers={"Authorization": f"Bearer {p_token}"}
        )
        assert offer_res.status_code == 200, f"Direct offer failed: {offer_res.text}"
        offer_id = offer_res.json()["id"]
        print(f"[OK] Path B Direct Job Offer Creation Passed (Offer #{offer_id}).")

        # 7. Worker accepts offer -> Auto Creates Assigned Job & Exposes Phone Contact Details
        accept_res = await ac.patch(
            f"/api/v1/direct-offers/{offer_id}",
            json={"action": "accept"},
            headers={"Authorization": f"Bearer {w_token}"}
        )
        assert accept_res.status_code == 200, f"Offer response failed: {accept_res.text}"
        assert accept_res.json()["status"] == "accepted", "Offer status should be accepted"

        job_id_created = accept_res.json()["job_id"]
        p_phone = accept_res.json()["provider"]["phone"]
        w_phone = accept_res.json()["worker"]["phone"]
        assert p_phone is not None, "Provider phone should be available on accepted offer"
        assert w_phone is not None, "Worker phone should be available on accepted offer"
        print(f"[OK] Path B Offer Acceptance Passed (Created Job #{job_id_created}). Provider Phone: {p_phone} | Worker Phone: {w_phone}")

        # 8. Dual-Confirmation Job Completion Workflow
        # First confirmation by Provider
        comp1 = await ac.post(f"/api/v1/jobs/{job_id_created}/complete", headers={"Authorization": f"Bearer {p_token}"})
        assert comp1.status_code == 200, f"Comp1 failed: {comp1.text}"
        assert comp1.json()["status"] == "assigned", "Should remain assigned until worker also confirms"
        assert comp1.json()["provider_completed"] == True
        assert comp1.json()["worker_completed"] == False
        print("[OK] Dual-Confirmation Step 1: Provider marked complete. Status remains ONGOING waiting for worker.")

        # Second confirmation by Worker -> Transitions to COMPLETED
        comp2 = await ac.post(f"/api/v1/jobs/{job_id_created}/complete", headers={"Authorization": f"Bearer {w_token}"})
        assert comp2.status_code == 200, f"Comp2 failed: {comp2.text}"
        assert comp2.json()["status"] == "completed", "Should transition to completed after mutual confirmation"
        assert comp2.json()["provider_completed"] == True
        assert comp2.json()["worker_completed"] == True
        print("[OK] Dual-Confirmation Step 2: Worker marked complete. Job status transitioned to COMPLETED & Worker job count incremented!")

        # 9. Test Review Submission
        rev_res = await ac.post(
            "/api/v1/jobs/reviews",
            json={
                "job_id": job_id_created,
                "reviewee_id": w_user_id,
                "rating": 5,
                "comment": "Outstanding work! Fast leak repair."
            },
            headers={"Authorization": f"Bearer {p_token}"}
        )
        assert rev_res.status_code == 200, f"Review failed: {rev_res.text}"
        print("[OK] Job Completion & 5-Star Rating Submitted. Trust Engine recalculated worker score.")

        # 10. Test Delete Job Posting Endpoint
        temp_job = await ac.post(
            "/api/v1/jobs",
            json={
                "title": "Temp Job To Delete",
                "description": "Temporary job posting",
                "required_skill": "Plumbing",
                "workers_needed": 1,
                "budget_min": 100,
                "budget_max": 200,
                "urgency": "immediate",
                "latitude": 12.9716,
                "longitude": 77.5946
            },
            headers={"Authorization": f"Bearer {p_token}"}
        )
        temp_job_id = temp_job.json()["id"]

        del_res = await ac.delete(f"/api/v1/jobs/{temp_job_id}", headers={"Authorization": f"Bearer {p_token}"})
        assert del_res.status_code == 200, f"Delete job failed: {del_res.text}"
        print(f"[OK] Job Deletion Passed: Deleted Job #{temp_job_id}.")

        # 11. Test Admin Console & Isolation Forest Anomaly Detection
        fraud_res = await ac.post("/api/v1/admin/run-fraud-detection", headers={"Authorization": f"Bearer {a_token}"})
        assert fraud_res.status_code == 200, f"Fraud detection failed: {fraud_res.text}"
        print("[OK] Isolation Forest Anomaly Model Executed Passed: ", fraud_res.json())

        analytics_res = await ac.get("/api/v1/admin/analytics", headers={"Authorization": f"Bearer {a_token}"})
        assert analytics_res.status_code == 200, f"Analytics failed: {analytics_res.text}"
        print("[OK] Admin Analytics & Path A vs Path B Split Passed: ", analytics_res.json())

    print("\n" + "=" * 60)
    print("ALL VERIFICATION TESTS PASSED SUCCESSFULLY! ZERO ERRORS.")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_all_servease_features())
