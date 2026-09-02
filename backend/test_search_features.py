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

    async with AsyncSessionLocal() as db:
        w_user = (await db.execute(select(User).where(User.role == UserRole.WORKER))).scalars().first()
        p_user = (await db.execute(select(User).where(User.role == UserRole.PROVIDER))).scalars().first()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create auth tokens with valid integer user IDs
        worker_token = create_access_token(str(w_user.id), "worker")
        provider_token = create_access_token(str(p_user.id), "provider")

        w_headers = {"Authorization": f"Bearer {worker_token}"}
        p_headers = {"Authorization": f"Bearer {provider_token}"}

        print("\n--- 1. Worker Directory Search Tests ---")
        
        # 1.1 Exact search
        r = await client.get("/api/v1/workers?q=Ramesh Kumar", headers=p_headers)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert len(data) >= 1, "Expected at least 1 worker for 'Ramesh Kumar'"
        assert any("Ramesh" in w["full_name"] for w in data)
        print(f"[PASS] Exact worker search: found {len(data)} result(s)")

        # 1.2 Case-insensitive & whitespace tolerant search
        r = await client.get("/api/v1/workers?q=%20%20RAMESH%20%20", headers=p_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert any("Ramesh" in w["full_name"] for w in data)
        print(f"[PASS] Case-insensitive & whitespace tolerant: found {len(data)} result(s)")

        # 1.3 Partial name search ("ram")
        r = await client.get("/api/v1/workers?q=ram", headers=p_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert any("ram" in w["full_name"].lower() for w in data)
        print(f"[PASS] Partial name search ('ram'): found {len(data)} result(s)")

        # 1.4 Skill search ("Plumbing")
        r = await client.get("/api/v1/workers?q=plumb", headers=p_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        print(f"[PASS] Skill search ('plumb'): found {len(data)} result(s)")

        # 1.5 Multi-word search ("ramesh plumb")
        r = await client.get("/api/v1/workers?q=ramesh%20plumb", headers=p_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        print(f"[PASS] Multi-word search ('ramesh plumb'): found {len(data)} result(s)")

        # 1.6 Non-matching search
        r = await client.get("/api/v1/workers?q=xyznonexistent999", headers=p_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 0, f"Expected 0 results, got {len(data)}"
        print(f"[PASS] Zero results search: returned {len(data)} result(s)")

        print("\n--- 2. Jobs Search Tests ---")

        # 2.1 Search by title
        r = await client.get("/api/v1/jobs?q=Plumbing", headers=w_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        print(f"[PASS] Job search by skill/title ('Plumbing'): found {len(data)} result(s)")

        # 2.2 Partial job search
        r = await client.get("/api/v1/jobs?q=kitc", headers=w_headers)
        assert r.status_code == 200
        data = r.json()
        print(f"[PASS] Partial job search ('kitc'): found {len(data)} result(s)")

        # 2.3 Provider name search in jobs
        r = await client.get("/api/v1/jobs?q=Priya", headers=w_headers)
        assert r.status_code == 200
        data = r.json()
        print(f"[PASS] Provider name search ('Priya'): found {len(data)} result(s)")

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
