import asyncio
import httpx
from app.seed import seed_database
from app.main import app

async def run_trust_and_rating_tests():
    print("=" * 70)
    print("ServEase Trust Score & Two-Way Rating System Test Suite")
    print("=" * 70)

    # 1. Initialize & Seed DB
    await seed_database()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # Auth: Login Worker 1 (Ramesh), Worker 2 (Suresh - unverified), Provider 1 (Priya), Provider 2 (Vimal)
        w1_login = await ac.post("/api/v1/auth/login", json={"email": "ramesh.plumber@gmail.com", "password": "worker123"})
        assert w1_login.status_code == 200, f"Worker login failed: {w1_login.text}"
        w1_token = w1_login.json()["access_token"]
        w1_user_id = w1_login.json()["user_id"]

        p1_login = await ac.post("/api/v1/auth/login", json={"email": "priya.sharma@gmail.com", "password": "provider123"})
        assert p1_login.status_code == 200, f"Provider login failed: {p1_login.text}"
        p1_token = p1_login.json()["access_token"]
        p1_user_id = p1_login.json()["user_id"]

        # Register a brand new Worker 3 (0 jobs, 0 ratings)
        import time
        w3_email = f"newbie_{int(time.time() * 1000)}@gmail.com"
        w3_reg = await ac.post("/api/v1/auth/register", json={
            "email": w3_email,
            "password": "newbiepassword123",
            "full_name": "Newbie Worker",
            "role": "worker"
        })
        assert w3_reg.status_code == 200, f"Register failed: {w3_reg.text}"
        w3_login = await ac.post("/api/v1/auth/login", json={"email": w3_email, "password": "newbiepassword123"})
        assert w3_login.status_code == 200
        w3_token = w3_login.json()["access_token"]
        w3_user_id = w3_login.json()["user_id"]

        # -------------------------------------------------------------
        # TEST 1: Cold Start Worker Trust Score (0 Completed Jobs)
        # -------------------------------------------------------------
        print("\n--- TEST 1: Cold-Start Worker (0 Completed Jobs) ---")
        w3_profile_res = await ac.get("/api/v1/workers/me", headers={"Authorization": f"Bearer {w3_token}"})
        assert w3_profile_res.status_code == 200
        w3_profile = w3_profile_res.json()
        print(f"New Worker Trust Score: {w3_profile['trust_score']}")
        print(f"New Worker Avg Rating: {w3_profile['avg_rating']}, Rating Count: {w3_profile['rating_count']}")
        assert w3_profile['trust_score'] < 50.0, f"Cold start worker should not have high trust score! Got {w3_profile['trust_score']}"
        assert w3_profile['avg_rating'] is None, "New worker should have None avg_rating"
        assert w3_profile['rating_count'] == 0, "New worker should have 0 rating_count"
        print("[PASS] Cold-start worker has honest neutral starting score (< 50.0) and 0 ratings.")

        # -------------------------------------------------------------
        # TEST 2: Provider Posts Job, Assigns Newbie Worker
        # -------------------------------------------------------------
        print("\n--- TEST 2: Job Lifecycle (Open -> Assigned -> Completed) ---")
        post_res = await ac.post("/api/v1/jobs", json={
            "title": "Fix Garden Tap Leak",
            "description": "Urgent tap leak in front yard",
            "required_skill": "Plumbing",
            "workers_needed": 1,
            "budget_min": 300,
            "budget_max": 500,
            "urgency": "immediate"
        }, headers={"Authorization": f"Bearer {p1_token}"})
        assert post_res.status_code == 200
        job_id = post_res.json()["id"]

        # Worker 3 applies
        app_res = await ac.post(f"/api/v1/jobs/{job_id}/apply", headers={"Authorization": f"Bearer {w3_token}"})
        assert app_res.status_code == 200
        app_id = app_res.json()["application_id"]

        # Provider accepts Worker 3
        resp_res = await ac.post(f"/api/v1/jobs/{job_id}/applications/{app_id}/respond?action=accept", headers={"Authorization": f"Bearer {p1_token}"})
        assert resp_res.status_code == 200

        # -------------------------------------------------------------
        # TEST 3: Attempt Rating BEFORE Job Completion (Must Fail with 400)
        # -------------------------------------------------------------
        print("\n--- TEST 3: Attempt Rating Before Job Completion ---")
        early_rate = await ac.post("/api/v1/jobs/reviews", json={
            "job_id": job_id,
            "overall_rating": 5,
            "category_ratings": {"service_quality": 5, "behavior": 5, "reliability": 5, "communication": 5},
            "comment": "Too early"
        }, headers={"Authorization": f"Bearer {p1_token}"})
        assert early_rate.status_code == 400, f"Rating before completion should return 400! Got {early_rate.status_code}"
        print(f"[PASS] Correctly blocked early rating attempt: {early_rate.json()['detail']}")

        # -------------------------------------------------------------
        # TEST 4: Attempt Rating by Unauthorized 3rd Party User (Must Fail with 403)
        # -------------------------------------------------------------
        print("\n--- TEST 4: Attempt Rating by Unauthorized User ---")
        # Dual-confirm job completion
        await ac.post(f"/api/v1/jobs/{job_id}/complete", headers={"Authorization": f"Bearer {p1_token}"})
        await ac.post(f"/api/v1/jobs/{job_id}/complete", headers={"Authorization": f"Bearer {w3_token}"})

        unauth_rate = await ac.post("/api/v1/jobs/reviews", json={
            "job_id": job_id,
            "overall_rating": 5,
            "category_ratings": {},
            "comment": "I was not in this job"
        }, headers={"Authorization": f"Bearer {w1_token}"})
        assert unauth_rate.status_code == 403, f"Unauthorized user should get 403! Got {unauth_rate.status_code}"
        print(f"[PASS] Correctly blocked unauthorized rating attempt: {unauth_rate.json()['detail']}")

        # -------------------------------------------------------------
        # TEST 5: Provider Rates Worker (5 Stars)
        # -------------------------------------------------------------
        print("\n--- TEST 5: Provider Rates Worker (5 Stars) ---")
        rate_worker_res = await ac.post("/api/v1/jobs/reviews", json={
            "job_id": job_id,
            "overall_rating": 5,
            "category_ratings": {
                "service_quality": 5,
                "behavior": 5,
                "reliability": 5,
                "communication": 5
            },
            "comment": "Punctual and great plumbing repair!"
        }, headers={"Authorization": f"Bearer {p1_token}"})
        assert rate_worker_res.status_code == 200, f"Rate worker failed: {rate_worker_res.text}"
        print("[PASS] Provider successfully rated worker with categories.")

        # Check Worker 3 updated profile
        w3_profile_after_1 = (await ac.get("/api/v1/workers/me", headers={"Authorization": f"Bearer {w3_token}"})).json()
        print(f"Worker 3 after 1 completed 5-star job: Trust Score = {w3_profile_after_1['trust_score']}, Avg Rating = {w3_profile_after_1['avg_rating']}, Rating Count = {w3_profile_after_1['rating_count']}")
        assert w3_profile_after_1['avg_rating'] == 5.0
        assert w3_profile_after_1['rating_count'] == 1
        # With Bayesian smoothing, 1 rating gives a moderate boost from 30.5 to ~42.7, not jumping to 95+
        assert 40.0 <= w3_profile_after_1['trust_score'] <= 70.0, f"Trust score after 1 job should be in ~40-70 range! Got {w3_profile_after_1['trust_score']}"
        print("[PASS] Worker rating and trust score updated deterministically with Bayesian smoothing.")

        # -------------------------------------------------------------
        # TEST 6: Prevent Duplicate Rating Attempt
        # -------------------------------------------------------------
        print("\n--- TEST 6: Duplicate Rating Attempt ---")
        dup_rate = await ac.post("/api/v1/jobs/reviews", json={
            "job_id": job_id,
            "overall_rating": 4,
            "category_ratings": {},
            "comment": "Trying to rate again"
        }, headers={"Authorization": f"Bearer {p1_token}"})
        assert dup_rate.status_code == 400, f"Duplicate rating should return 400! Got {dup_rate.status_code}"
        print(f"[PASS] Duplicate rating correctly rejected: {dup_rate.json()['detail']}")

        # -------------------------------------------------------------
        # TEST 7: Worker Rates Provider
        # -------------------------------------------------------------
        print("\n--- TEST 7: Worker Rates Provider ---")
        rate_provider_res = await ac.post("/api/v1/jobs/reviews", json={
            "job_id": job_id,
            "overall_rating": 5,
            "category_ratings": {
                "behavior": 5,
                "communication": 5,
                "payment_experience": 5,
                "respect_professionalism": 5
            },
            "comment": "Great provider, prompt payment!"
        }, headers={"Authorization": f"Bearer {w3_token}"})
        assert rate_provider_res.status_code == 200, f"Rate provider failed: {rate_provider_res.text}"
        print("[PASS] Worker successfully rated provider with 4 categories.")

        # Check Provider Profile
        p1_profile = (await ac.get("/api/v1/auth/providers/me", headers={"Authorization": f"Bearer {p1_token}"})).json()
        assert p1_profile['avg_rating'] is not None and p1_profile['avg_rating'] > 0
        assert p1_profile['rating_count'] >= 1
        print("[PASS] Provider profile displays received ratings from workers.")

        # -------------------------------------------------------------
        # TEST 8: Check Two-Way Job Ratings Status Endpoint
        # -------------------------------------------------------------
        print("\n--- TEST 8: Two-Way Job Ratings Status Endpoint ---")
        ratings_status = (await ac.get(f"/api/v1/jobs/{job_id}/ratings", headers={"Authorization": f"Bearer {p1_token}"})).json()
        print(f"Job Ratings Status: worker_rated={ratings_status['worker_rated_provider']}, provider_rated={ratings_status['provider_rated_worker']}")
        assert ratings_status['is_completed'] is True
        assert ratings_status['worker_rated_provider'] is True
        assert ratings_status['provider_rated_worker'] is True
        assert ratings_status['worker_review'] is not None
        assert ratings_status['provider_review'] is not None
        print("[PASS] Two-way job rating status endpoint verified.")

        # -------------------------------------------------------------
        # TEST 9: Detailed User Rating Summary Endpoint
        # -------------------------------------------------------------
        print("\n--- TEST 9: User Rating Summary Endpoint ---")
        summary_res = await ac.get(f"/api/v1/jobs/users/{w3_user_id}/rating-summary")
        assert summary_res.status_code == 200
        summary = summary_res.json()
        print(f"Worker 3 Summary: Avg = {summary['avg_rating']}, Count = {summary['rating_count']}, Category Averages = {summary['category_averages']}")
        assert summary['avg_rating'] == 5.0
        assert summary['rating_count'] == 1
        assert "service_quality" in summary['category_averages']
        print("[PASS] Detailed user rating summary endpoint returned category breakdown.")

    print("\n" + "=" * 70)
    print("ALL TRUST SCORE & TWO-WAY RATING TESTS PASSED! ZERO ERRORS.")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_trust_and_rating_tests())
