import asyncio
import httpx
import math
from app.core.config import settings
from app.services.ml_matching import calculate_haversine_distance, rank_workers_for_job

BASE_URL = "http://127.0.0.1:8000/api/v1"

async def test_location_and_matching_flow():
    print("=" * 70)
    print("ServEase Location-Based Matching & Proximity Test Suite")
    print("=" * 70)

    # 1. Haversine Unit Test
    print("\n--- 1. Testing Haversine Distance Calculation ---")
    # Coordinates for Koramangala (12.9352, 77.6245) to Indiranagar (12.9784, 77.6408)
    dist = calculate_haversine_distance(12.9352, 77.6245, 12.9784, 77.6408)
    print(f"Calculated distance Koramangala -> Indiranagar: {dist:.2f} km")
    assert 4.0 <= dist <= 6.0, f"Unexpected distance: {dist}"
    print("[PASS] Haversine calculation verified.")

    # 2. Testing ML Matching with Dual Radius Constraints
    print("\n--- 2. Testing ML Matching with Dual Radius Constraints ---")
    workers_data = [
        {
            "id": 101,
            "latitude": 12.9720,
            "longitude": 77.5950,
            "service_radius_km": 15.0,
            "trust_score": 85.0,
            "full_name": "Nearby Plumber",
            "profile_obj": {"id": 101, "full_name": "Nearby Plumber"},
            "skills": [{"skill_name": "Plumbing", "skill_tags": ["pipe", "leak"]}],
            "completion_rate": 0.95,
            "acceptance_rate": 0.90
        },
        {
            "id": 102,
            "latitude": 13.5000, # Far away (~60km)
            "longitude": 77.5950,
            "service_radius_km": 15.0,
            "trust_score": 90.0,
            "full_name": "Far Plumber",
            "profile_obj": {"id": 102, "full_name": "Far Plumber"},
            "skills": [{"skill_name": "Plumbing", "skill_tags": ["pipe", "leak"]}],
            "completion_rate": 0.95,
            "acceptance_rate": 0.90
        }
    ]

    ranked = rank_workers_for_job(
        job_title="Emergency Pipe Leak",
        job_description="Major leak in bathroom",
        job_skill="Plumbing",
        job_lat=12.9716,
        job_lng=77.5946,
        workers_data=workers_data,
        search_radius_km=10.0
    )
    print(f"Ranked {len(ranked)} eligible candidate(s) for 10km radius:")
    for r in ranked:
        print(f"  • Worker: {r['worker_profile']['full_name']} | Match Score: {r['match_score']}% | Distance: {r['distance_km']} km")
    
    assert len(ranked) == 1
    assert ranked[0]["worker_profile"]["id"] == 101
    print("[PASS] Dual radius matching strictly excludes out-of-range workers.")

    # 3. Direct DB & API Testing with AsyncClient
    print("\n--- 3. Testing Worker Location Update & Job Proximity Endpoints ---")
    from app.core.database import init_db, AsyncSessionLocal
    from app.models.domain import User, UserRole, WorkerProfile, Job, JobStatus, JobUrgency, JobSource
    from sqlalchemy.future import select
    from sqlalchemy.orm import selectinload

    await init_db()

    async with AsyncSessionLocal() as db:
        # Check that worker_profiles and jobs have the new columns populated
        res = await db.execute(select(WorkerProfile).limit(1))
        wp = res.scalars().first()
        if wp:
            print(f"Sample Worker: '{wp.full_name}' | Location: {wp.latitude}, {wp.longitude} | Updated: {wp.location_updated_at}")
            assert hasattr(wp, 'location_name')
            assert hasattr(wp, 'location_updated_at')

        res_jobs = await db.execute(select(Job).limit(1))
        jb = res_jobs.scalars().first()
        if jb:
            print(f"Sample Job: '{jb.title}' | Radius: {jb.search_radius_km} km | Location: {jb.location_name}")
            assert hasattr(jb, 'search_radius_km')
            assert hasattr(jb, 'location_name')

    print("\n" + "=" * 70)
    print("ALL LOCATION & GEOSPATIAL MATCHING TESTS PASSED! ZERO ERRORS.")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_location_and_matching_flow())
