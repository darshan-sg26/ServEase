import asyncio
import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db, get_db, AsyncSessionLocal
from app.seed import seed_database
from app.core.security import create_access_token
from app.models.domain import User, UserRole
from sqlalchemy.future import select

async def run_search_tests():
    print("=" * 70)
    print("ServEase Search Features Automated Test Suite")
    print("=" * 70)

    # Initialize and seed if needed
    await init_db()
    await seed_database()

    from app.models.domain import WorkerProfile, ProviderProfile, Job
    from sqlalchemy.orm import selectinload

    async with AsyncSessionLocal() as db:
        w_user = (await db.execute(select(User).where(User.role == UserRole.WORKER))).scalars().first()
        p_user = (await db.execute(select(User).where(User.role == UserRole.PROVIDER))).scalars().first()
        w_prof = (await db.execute(select(WorkerProfile).options(selectinload(WorkerProfile.skills)))).scalars().first()
        p_prof = (await db.execute(select(ProviderProfile))).scalars().first()
        sample_job = (await db.execute(select(Job))).scalars().first()
        worker_name = w_prof.full_name
        skill_term = w_prof.skills[0].skill_name if (w_prof.skills and len(w_prof.skills) > 0) else "Plumbing"
        prov_name = p_prof.full_name if p_prof else "Provider"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create auth tokens with valid integer user IDs
        worker_token = create_access_token(str(w_user.id), "worker")
        provider_token = create_access_token(str(p_user.id), "provider")

        w_headers = {"Authorization": f"Bearer {worker_token}"}
        p_headers = {"Authorization": f"Bearer {provider_token}"}

        print("\n--- 1. Worker Directory Search Tests ---")
        
        # 1.1 Exact search
        r = await client.get(f"/api/v1/workers?q={worker_name}", headers=p_headers)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert len(data) >= 1, f"Expected at least 1 worker for '{worker_name}'"
        print(f"[PASS] Exact worker search: found {len(data)} result(s)")

        # 1.2 Case-insensitive & whitespace tolerant search
        r = await client.get(f"/api/v1/workers?q=%20%20{worker_name.upper()}%20%20", headers=p_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        print(f"[PASS] Case-insensitive & whitespace tolerant: found {len(data)} result(s)")

        # 1.3 Partial name search
        partial_name = worker_name[:3].lower()
        r = await client.get(f"/api/v1/workers?q={partial_name}", headers=p_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        print(f"[PASS] Partial name search ('{partial_name}'): found {len(data)} result(s)")

        # 1.4 Skill search
        r = await client.get(f"/api/v1/workers?q={skill_term}", headers=p_headers)
        assert r.status_code == 200
        data = r.json()
        print(f"[PASS] Skill search ('{skill_term}'): found {len(data)} result(s)")

        # 1.5 Multi-word search
        r = await client.get(f"/api/v1/workers?q={worker_name}%20{skill_term}", headers=p_headers)
        assert r.status_code == 200
        data = r.json()
        print(f"[PASS] Multi-word search: found {len(data)} result(s)")

        # 1.6 Non-matching search
        r = await client.get("/api/v1/workers?q=xyznonexistent999", headers=p_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 0, f"Expected 0 results, got {len(data)}"
        print(f"[PASS] Zero results search: returned {len(data)} result(s)")

        print("\n--- 2. Jobs Search Tests ---")

        # 2.1 Search by title
        job_title = sample_job.title if sample_job else "Plumbing"
        r = await client.get(f"/api/v1/jobs?q={job_title[:4]}", headers=w_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        print(f"[PASS] Job search by title ('{job_title[:4]}'): found {len(data)} result(s)")

        # 2.2 Partial job search
        r = await client.get("/api/v1/jobs?q=a", headers=w_headers)
        assert r.status_code == 200
        data = r.json()
        print(f"[PASS] Partial job search: found {len(data)} result(s)")

        # 2.3 Provider name search in jobs
        r = await client.get(f"/api/v1/jobs?q={prov_name[:3]}", headers=w_headers)
        assert r.status_code == 200
        data = r.json()
        print(f"[PASS] Provider name search ('{prov_name[:3]}'): found {len(data)} result(s)")

        # 2.4 Non-matching job search
        r = await client.get("/api/v1/jobs?q=nonexistentjobquery123", headers=w_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 0
        print(f"[PASS] Zero results job search: returned {len(data)} result(s)")

        print("\n--- 3. Direct Offers Search Tests ---")

        # 3.1 Search direct offers
        r = await client.get("/api/v1/direct-offers?q=Offer", headers=w_headers)
        assert r.status_code == 200
        data = r.json()
        print(f"[PASS] Direct offers search ('Offer'): found {len(data)} result(s)")

        # 3.2 Non-matching direct offers search
        r = await client.get("/api/v1/direct-offers?q=nonexistentoffer999", headers=w_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 0
        print(f"[PASS] Zero results direct offers search: returned {len(data)} result(s)")

    print("\n" + "=" * 70)
    print("ALL SEARCH FEATURE BACKEND TESTS PASSED! ZERO ERRORS.")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_search_tests())
