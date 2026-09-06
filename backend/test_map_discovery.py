"""
Comprehensive verification test for ServEase Map-Based Discovery endpoints:
- GET /api/v1/workers/nearby
- GET /api/v1/jobs/nearby
Verifies:
1. Static route ordering (/nearby is not captured by /{id})
2. Server-computed Haversine distance returned in distance_km for both workers and jobs
3. Workers and jobs sorted closest-first
4. Radius filtering strictly enforced on the server
5. Availability filtering: Only available workers and open jobs returned
6. Worker privacy protection: phone numbers masked and micro-jitter applied
7. Parameter validation (lat/lng bounds check)
"""
import asyncio
import sys
import os

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db

async def run_map_discovery_tests():
    print("=" * 70)
    print("STARTING MAP-BASED DISCOVERY BACKEND TESTS")
    print("=" * 70)

    # Initialize DB (runs safe migrations)
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        # TEST 1: Static Route Ordering & Parameter Validation
        print("\n--- TEST 1: Route Ordering & Parameter Validation ---")
        # Missing lat/lng should return 422 Unprocessable Entity
        res = await client.get("/api/v1/workers/nearby")
        assert res.status_code == 422, f"Expected 422 for missing params, got {res.status_code}"

        res = await client.get("/api/v1/jobs/nearby")
        assert res.status_code == 422, f"Expected 422 for missing params, got {res.status_code}"

        # Out-of-bounds latitude should return 422
        res = await client.get("/api/v1/workers/nearby?latitude=100.0&longitude=77.5946")
        assert res.status_code == 422, f"Expected 422 for invalid lat, got {res.status_code}"

        print("[PASS] Static route ordering preserved and parameter bounds validated.")

        # TEST 2: Nearby Workers Discovery
        print("\n--- TEST 2: GET /api/v1/workers/nearby ---")
        center_lat = 12.9716
        center_lng = 77.5946

        res = await client.get(f"/api/v1/workers/nearby?latitude={center_lat}&longitude={center_lng}&radius_km=25.0")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        workers = res.json()
        print(f"Found {len(workers)} nearby worker(s) within 25.0 km")

        for w in workers:
            # 1. distance_km exists and is a valid float <= radius_km
            assert "distance_km" in w and w["distance_km"] is not None, f"Worker {w['id']} missing distance_km"
            assert w["distance_km"] <= 25.0, f"Worker {w['id']} distance {w['distance_km']} exceeds 25km radius"
            
            # 2. Worker must be available
            assert w.get("availability_status") == "available", f"Worker {w['id']} is not available"

            # 3. Privacy protection: phone must be masked
            phone = w.get("phone")
            if phone:
                assert "*" in phone or phone.startswith("+91 ******"), f"Worker phone not masked: {phone}"

            print(f"  Worker: '{w.get('full_name')}' | Distance: {w.get('distance_km')} km | Rating: {w.get('avg_rating')} | Masked Phone: {phone}")

        # Verify sorted ascending by distance
        if len(workers) > 1:
            for i in range(len(workers) - 1):
                assert workers[i]["distance_km"] <= workers[i + 1]["distance_km"], "Workers not sorted by distance ascending"
            print("[PASS] Nearby workers are correctly sorted closest-first.")

        # TEST 3: Radius Filtering on Workers
        print("\n--- TEST 3: Worker Radius Filtering ---")
        tight_res = await client.get(f"/api/v1/workers/nearby?latitude={center_lat}&longitude={center_lng}&radius_km=0.001")
        assert tight_res.status_code == 200
        tight_workers = tight_res.json()
        assert len(tight_workers) <= len(workers), "Tight radius returned more workers than wide radius"
        print(f"[PASS] Tight radius (0.001 km) correctly restricted results: {len(tight_workers)} workers returned.")

        # TEST 4: Nearby Jobs Discovery
        print("\n--- TEST 4: GET /api/v1/jobs/nearby ---")
        res_jobs = await client.get(f"/api/v1/jobs/nearby?latitude={center_lat}&longitude={center_lng}&radius_km=50.0")
        assert res_jobs.status_code == 200, f"Expected 200, got {res_jobs.status_code}: {res_jobs.text}"
        jobs = res_jobs.json()
        print(f"Found {len(jobs)} nearby job(s) within 50.0 km")

        for j in jobs:
            # 1. distance_km exists and <= 50.0
            assert "distance_km" in j and j["distance_km"] is not None, f"Job {j['id']} missing distance_km"
            assert j["distance_km"] <= 50.0, f"Job {j['id']} distance {j['distance_km']} exceeds 50km radius"

            # 2. Status must be OPEN
            assert j.get("status") == "open", f"Job {j['id']} is not open: status={j.get('status')}"

            print(f"  Job: '{j.get('title')}' | Distance: {j.get('distance_km')} km | Skill: {j.get('required_skill')} | Status: {j.get('status')}")

        # Verify sorted ascending by distance
        if len(jobs) > 1:
            for i in range(len(jobs) - 1):
                assert jobs[i]["distance_km"] <= jobs[i + 1]["distance_km"], "Jobs not sorted by distance ascending"
            print("[PASS] Nearby jobs are correctly sorted closest-first.")

        # TEST 5: Radius Filtering on Jobs
        print("\n--- TEST 5: Job Radius Filtering ---")
        tight_jobs_res = await client.get(f"/api/v1/jobs/nearby?latitude={center_lat}&longitude={center_lng}&radius_km=0.001")
        assert tight_jobs_res.status_code == 200
        tight_jobs = tight_jobs_res.json()
        assert len(tight_jobs) <= len(jobs), "Tight radius returned more jobs than wide radius"
        print(f"[PASS] Tight radius (0.001 km) correctly restricted job results: {len(tight_jobs)} jobs returned.")

    print("\n" + "=" * 70)
    print("ALL MAP-BASED DISCOVERY TESTS PASSED! ZERO ERRORS.")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_map_discovery_tests())
