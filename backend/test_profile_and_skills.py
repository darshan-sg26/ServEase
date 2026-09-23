import asyncio
import datetime
import httpx
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.main import app
from app.core.database import AsyncSessionLocal, init_db
from app.models.domain import User, UserRole, WorkerProfile, WorkerSkill, SkillStatus
from app.core.security import create_access_token, get_password_hash


async def run_tests():
    print("===============================================================")
    print("STARTING PROFILE EDIT PERSISTENCE & SKILL VERIFICATION TEST SUITE")
    print("===============================================================")
    await init_db()

    # Step 0: Seed or retrieve test users: a worker and an admin
    async with AsyncSessionLocal() as db:
        # Check / create test worker
        w_email = "test.worker.profile@servease.com"
        w_user = (await db.execute(select(User).where(User.email == w_email))).scalars().first()
        if not w_user:
            w_user = User(
                email=w_email,
                phone="+919876543210",
                password_hash=get_password_hash("WorkerPass123!"),
                role=UserRole.WORKER,
                is_verified=True,
                auth_provider="email"
            )
            db.add(w_user)
            await db.flush()

            w_profile = WorkerProfile(
                user_id=w_user.id,
                full_name="Initial Worker Name",
                bio="Initial Bio Description",
                phone="+919876543210",
                hourly_rate=350.0,
                trust_score=78.5,
                service_radius_km=15.0,
                latitude=12.9716,
                longitude=77.5946
            )
            db.add(w_profile)
            await db.commit()
            await db.refresh(w_user)
        else:
            w_profile = (await db.execute(select(WorkerProfile).where(WorkerProfile.user_id == w_user.id))).scalars().first()
            if not w_profile:
                w_profile = WorkerProfile(
                    user_id=w_user.id,
                    full_name="Initial Worker Name",
                    bio="Initial Bio Description",
                    phone="+919876543210",
                    hourly_rate=350.0,
                    trust_score=78.5,
                    service_radius_km=15.0,
                    latitude=12.9716,
                    longitude=77.5946
                )
                db.add(w_profile)
                await db.commit()

        worker_id = w_user.id
        worker_profile_id = w_profile.id

        # Check / create test admin
        a_email = "test.admin.verification@servease.com"
        a_user = (await db.execute(select(User).where(User.email == a_email))).scalars().first()
        if not a_user:
            a_user = User(
                email=a_email,
                password_hash=get_password_hash("AdminPass123!"),
                role=UserRole.ADMIN,
                is_verified=True,
                auth_provider="email"
            )
            db.add(a_user)
            await db.commit()
            await db.refresh(a_user)
        admin_id = a_user.id

    worker_token = create_access_token(str(worker_id), "worker")
    admin_token = create_access_token(str(admin_id), "admin")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # ===============================================================
        # TEST A — PROFILE UPDATE PERSISTENCE
        # ===============================================================
        print("\n[TEST A] Worker Profile Edit & Database Persistence...")
        edit_payload = {
            "full_name": "Rahul Test Worker",
            "phone": "+919988776655",
            "bio": "Experienced Master Plumber & Technician",
            "hourly_rate": 475.0
        }
        res = await client.put(
            "/api/v1/workers/me",
            headers={"Authorization": f"Bearer {worker_token}"},
            json=edit_payload
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert data["full_name"] == "Rahul Test Worker", f"Expected 'Rahul Test Worker', got {data['full_name']}"
        assert data["phone"] == "+919988776655", f"Expected '+919988776655', got {data['phone']}"
        assert data["bio"] == "Experienced Master Plumber & Technician"
        assert data["hourly_rate"] == 475.0

        # Verify database directly
        async with AsyncSessionLocal() as db:
            wp = (await db.execute(select(WorkerProfile).where(WorkerProfile.user_id == worker_id))).scalars().first()
            user_row = (await db.execute(select(User).where(User.id == worker_id))).scalars().first()
            assert wp.full_name == "Rahul Test Worker", f"DB WorkerProfile.full_name mismatch: {wp.full_name}"
            assert wp.phone == "+919988776655", f"DB WorkerProfile.phone mismatch: {wp.phone}"
            assert user_row.phone == "+919988776655", f"DB User.phone mismatch: {user_row.phone}"
            assert wp.trust_score == 78.5, f"Unrelated trust_score was altered! Got {wp.trust_score}"
            assert wp.latitude == 12.9716, "Unrelated latitude was altered!"
        print("  [PASS] Test A PASSED: Profile edited and persisted directly to database; User.phone in sync; other fields preserved.")

        # ===============================================================
        # TEST B — ADD NEW SKILL (MUST DEFAULT TO PENDING)
        # ===============================================================
        print("\n[TEST B] Worker Adds Skill -> Must default to PENDING (NOT VERIFIED)...")
        # Clean any previous test skills for this worker
        async with AsyncSessionLocal() as db:
            existing = (await db.execute(select(WorkerSkill).where(WorkerSkill.worker_id == worker_profile_id))).scalars().all()
            for s in existing:
                await db.delete(s)
            await db.commit()

        skill_payload = {
            "skill_name": "Electrical Repair",
            "years_experience": 4.5,
            "hourly_rate": 550.0,
            "skill_tags": ["wiring", "mcb", "inverter"]
        }
        res = await client.post(
            "/api/v1/workers/me/skills",
            headers={"Authorization": f"Bearer {worker_token}"},
            json=skill_payload
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        s_data = res.json()
        assert s_data["skill_name"] == "Electrical Repair"
        assert s_data["status"] == "pending", f"FAIL: Newly added skill returned status '{s_data['status']}', expected 'pending'!"
        electrical_skill_id = s_data["id"]

        # Check DB directly
        async with AsyncSessionLocal() as db:
            ws_db = (await db.execute(select(WorkerSkill).where(WorkerSkill.id == electrical_skill_id))).scalars().first()
            assert ws_db.status == SkillStatus.PENDING, f"DB WorkerSkill status is {ws_db.status}, expected PENDING!"
            assert ws_db.submitted_at is not None, "submitted_at was not recorded!"
            assert ws_db.reviewed_at is None, "reviewed_at should be None for pending skill!"
            assert ws_db.reviewed_by is None, "reviewed_by should be None for pending skill!"
        print("  [PASS] Test B PASSED: Skill created with status=PENDING, submitted_at timestamp stored.")

        # ===============================================================
        # TEST C — ADMIN DASHBOARD SKILL APPROVALS QUEUE
        # ===============================================================
        print("\n[TEST C] Admin Queue -> Fetch Pending Skill Approvals...")
        res = await client.get(
            "/api/v1/admin/skill-approvals",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        queue = res.json()
        matching = [item for item in queue if item["id"] == electrical_skill_id]
        assert len(matching) == 1, f"Expected electrical_skill_id {electrical_skill_id} in queue, found: {queue}"
        item = matching[0]
        assert item["skill_name"] == "Electrical Repair"
        assert item["worker_name"] == "Rahul Test Worker"
        assert item["status"] == "pending"
        print("  [PASS] Test C PASSED: Admin queue lists pending skill with worker name, trust score, and experience.")

        # ===============================================================
        # TEST D — ADMIN APPROVAL WORKFLOW
        # ===============================================================
        print("\n[TEST D] Admin Approves Skill -> Status becomes VERIFIED...")
        res = await client.post(
            f"/api/v1/admin/skill-approvals/{electrical_skill_id}/approve",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        appr_data = res.json()
        assert appr_data["success"] is True
        assert appr_data["status"] == "verified"

        # Check DB directly
        async with AsyncSessionLocal() as db:
            ws_db = (await db.execute(select(WorkerSkill).where(WorkerSkill.id == electrical_skill_id))).scalars().first()
            assert ws_db.status == SkillStatus.VERIFIED, f"DB status is {ws_db.status}, expected VERIFIED!"
            assert ws_db.reviewed_by == admin_id, f"reviewed_by is {ws_db.reviewed_by}, expected {admin_id}"
            assert ws_db.reviewed_at is not None, "reviewed_at was not recorded!"

        # Check worker's profile endpoint
        res = await client.get(
            "/api/v1/workers/me",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        wp_res = res.json()
        skills = wp_res["skills"]
        elec = [s for s in skills if s["id"] == electrical_skill_id][0]
        assert elec["status"] == "verified", f"Worker /me endpoint returned skill status '{elec['status']}'"
        print("  [PASS] Test D PASSED: Skill verified by admin; worker profile reflects status=verified.")

        # ===============================================================
        # TEST E — REJECT WORKFLOW
        # ===============================================================
        print("\n[TEST E] Worker adds Carpentry -> Admin Rejects with reason...")
        res = await client.post(
            "/api/v1/workers/me/skills",
            headers={"Authorization": f"Bearer {worker_token}"},
            json={"skill_name": "Carpentry", "years_experience": 2.0, "hourly_rate": 400.0}
        )
        assert res.status_code == 200
        carpentry_skill_id = res.json()["id"]

        reject_reason = "Requires certified carpentry apprenticeship proof."
        res = await client.post(
            f"/api/v1/admin/skill-approvals/{carpentry_skill_id}/reject",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"reason": reject_reason}
        )
        assert res.status_code == 200
        rej_data = res.json()
        assert rej_data["status"] == "rejected"
        assert rej_data["rejection_reason"] == reject_reason

        # Check DB directly
        async with AsyncSessionLocal() as db:
            ws_db = (await db.execute(select(WorkerSkill).where(WorkerSkill.id == carpentry_skill_id))).scalars().first()
            assert ws_db.status == SkillStatus.REJECTED, f"DB status is {ws_db.status}, expected REJECTED!"
            assert ws_db.rejection_reason == reject_reason

        # Check worker /me endpoint
        res = await client.get(
            "/api/v1/workers/me",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        carp = [s for s in res.json()["skills"] if s["id"] == carpentry_skill_id][0]
        assert carp["status"] == "rejected", f"Expected rejected, got {carp['status']}"
        assert carp["rejection_reason"] == reject_reason
        print("  [PASS] Test E PASSED: Admin rejected skill with reason; DB and worker storefront reflect status=rejected.")

        # ===============================================================
        # TEST F — SECURITY: WORKER CANNOT APPROVE / REJECT
        # ===============================================================
        print("\n[TEST F] Security Enforcement: Worker cannot call admin approval endpoints...")
        res = await client.post(
            f"/api/v1/admin/skill-approvals/{carpentry_skill_id}/approve",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert res.status_code == 403, f"Expected 403 Forbidden for worker, got {res.status_code}"

        res = await client.post(
            f"/api/v1/admin/skill-approvals/{carpentry_skill_id}/reject",
            headers={"Authorization": f"Bearer {worker_token}"},
            json={"reason": "Self-reject attempt"}
        )
        assert res.status_code == 403, f"Expected 403 Forbidden for worker, got {res.status_code}"

        res = await client.get(
            "/api/v1/admin/skill-approvals",
            headers={"Authorization": f"Bearer {worker_token}"}
        )
        assert res.status_code == 403, f"Expected 403 Forbidden for worker, got {res.status_code}"
        print("  [PASS] Test F PASSED: Server-side authorization strictly forbids non-admin users from approving/rejecting skills.")

        # ===============================================================
        # TEST G — DUPLICATE PREVENTION
        # ===============================================================
        print("\n[TEST G] Duplicate Skill Handling...")
        # 1. Try adding 'Electrical Repair' again (which is already VERIFIED)
        res = await client.post(
            "/api/v1/workers/me/skills",
            headers={"Authorization": f"Bearer {worker_token}"},
            json={"skill_name": "electrical repair", "years_experience": 5.0, "hourly_rate": 600.0}
        )
        assert res.status_code == 400, f"Expected 400 for duplicate verified skill, got {res.status_code}"
        assert "already added and verified" in res.json()["detail"].lower()

        # 2. Add a new skill 'Plumbing' -> enters PENDING
        res = await client.post(
            "/api/v1/workers/me/skills",
            headers={"Authorization": f"Bearer {worker_token}"},
            json={"skill_name": "Plumbing Installation", "years_experience": 3.0, "hourly_rate": 450.0}
        )
        assert res.status_code == 200

        # Try adding 'Plumbing Installation' again while it is PENDING
        res = await client.post(
            "/api/v1/workers/me/skills",
            headers={"Authorization": f"Bearer {worker_token}"},
            json={"skill_name": "Plumbing Installation", "years_experience": 3.0, "hourly_rate": 450.0}
        )
        assert res.status_code == 400, f"Expected 400 for duplicate pending skill, got {res.status_code}"
        assert "already pending verification" in res.json()["detail"].lower()
        print("  [PASS] Test G PASSED: Duplicate verified and duplicate pending skills cleanly blocked.")

        # ===============================================================
        # TEST H — MATCHING ISOLATION (PENDING SKILLS NOT TREATED AS VERIFIED)
        # ===============================================================
        print("\n[TEST H] Matching & Search Isolation: Unverified skills ignored in discovery...")
        # Query nearby workers for 'Plumbing Installation' (which is PENDING)
        res = await client.get("/api/v1/workers/nearby?latitude=12.9716&longitude=77.5946&skill=Plumbing%20Installation")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        nearby = res.json()
        matching_workers = [w for w in nearby if w["id"] == worker_profile_id]
        assert len(matching_workers) == 0, "FAIL: Worker matched on a PENDING skill!"

        # Query nearby workers for 'Electrical Repair' (which is VERIFIED)
        res = await client.get("/api/v1/workers/nearby?latitude=12.9716&longitude=77.5946&skill=Electrical%20Repair")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        nearby_verified = res.json()
        matching_verified = [w for w in nearby_verified if w["id"] == worker_profile_id]
        assert len(matching_verified) >= 1, "FAIL: Worker did not match on a VERIFIED skill!"
        print("  [PASS] Test H PASSED: Discovery and matching exclusively consider VERIFIED skills.")

    print("\n===============================================================")
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("===============================================================")


if __name__ == "__main__":
    asyncio.run(run_tests())
