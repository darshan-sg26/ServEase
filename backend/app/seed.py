import asyncio
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import engine, AsyncSessionLocal, Base
from app.core.security import get_password_hash
from app.models.domain import (
    User, UserRole, WorkerProfile, WorkerSkill, ProviderProfile, Job, JobUrgency,
    JobSource, JobStatus, DirectOffer, DirectOfferStatus, Review, AvailabilityStatus, VerificationStatus
)
from app.services.trust_engine import compute_and_update_trust_score
from app.services.fraud_engine import run_isolation_forest_fraud_detection

async def seed_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Check if already seeded
        res = await db.execute(select(User))
        if res.scalars().first():
            print("Database already contains data. Skipping seeding.")
            return

        print("Seeding ServEase database with realistic VTU project demo data...")

        # 1. Admin User
        admin = User(
            email="admin@servease.com",
            password_hash=get_password_hash("admin123"),
            role=UserRole.ADMIN,
            is_verified=True
        )
        db.add(admin)

        # 2. Worker Users & Profiles
        workers_data = [
            {
                "email": "ramesh.plumber@gmail.com",
                "name": "Ramesh Kumar",
                "phone": "+919876543210",
                "lat": 12.9716, "lng": 77.5946, # Central Bengaluru
                "bio": "Certified master plumber with 8+ years experience in domestic pipe repair, sanitary fittings, and leak detection.",
                "status": AvailabilityStatus.AVAILABLE,
                "verification": VerificationStatus.VERIFIED,
                "skills": [
                    {"name": "Plumbing", "exp": 8.0, "rate": 450.0, "tags": ["pipe repair", "leak fix", "sanitary", "water heater", "tap installation"]},
                    {"name": "Drainage Repair", "exp": 5.0, "rate": 500.0, "tags": ["clog removal", "sewage pipe", "drainage"]}
                ]
            },
            {
                "email": "suresh.electrician@gmail.com",
                "name": "Suresh Gowda",
                "phone": "+919876543211",
                "lat": 12.9352, "lng": 77.6245, # Koramangala
                "bio": "Licensed ITI electrician specializing in home wiring, circuit breaker maintenance, and appliance repair.",
                "status": AvailabilityStatus.AVAILABLE,
                "verification": VerificationStatus.VERIFIED,
                "skills": [
                    {"name": "Electrical Wiring", "exp": 6.0, "rate": 500.0, "tags": ["wiring", "mcb repair", "switchboard", "fan installation", "inverter"]},
                    {"name": "Appliance Repair", "exp": 4.0, "rate": 400.0, "tags": ["washing machine", "refrigerator", "geyser repair"]}
                ]
            },
            {
                "email": "manjunath.driver@gmail.com",
                "name": "Manjunath V",
                "phone": "+919876543212",
                "lat": 12.9784, "lng": 77.6408, # Indiranagar
                "bio": "Punctual commercial driver with valid yellow-badge license. Experienced in manual & automatic SUVs.",
                "status": AvailabilityStatus.AVAILABLE,
                "verification": VerificationStatus.VERIFIED,
                "skills": [
                    {"name": "Personal Driving", "exp": 7.0, "rate": 600.0, "tags": ["chauffeur", "outstation trip", "city driving", "automatic car"]}
                ]
            },
            {
                "email": "anita.domestic@gmail.com",
                "name": "Anita Devi",
                "phone": "+919876543213",
                "lat": 12.9279, "lng": 77.5830, # Jayanagar
                "bio": "Background verified home cook and domestic manager. Specialized in South & North Indian cuisine.",
                "status": AvailabilityStatus.AVAILABLE,
                "verification": VerificationStatus.VERIFIED,
                "skills": [
                    {"name": "Home Cooking", "exp": 10.0, "rate": 350.0, "tags": ["cooking", "meal prep", "catering", "south indian cook"]},
                    {"name": "Housekeeping", "exp": 5.0, "rate": 300.0, "tags": ["deep cleaning", "dusting", "laundry"]}
                ]
            },
            {
                "email": "karan.carpenter@gmail.com",
                "name": "Karan Sharma",
                "phone": "+919876543214",
                "lat": 13.0358, "lng": 77.5970, # Hebbal
                "bio": "Custom furniture maker and modular kitchen repair expert with high precision tools.",
                "status": AvailabilityStatus.BUSY,
                "verification": VerificationStatus.PENDING,
                "skills": [
                    {"name": "Carpentry", "exp": 9.0, "rate": 550.0, "tags": ["furniture repair", "door lock", "modular kitchen", "wood polishing"]}
                ]
            }
        ]

        worker_objs = []
        for wd in workers_data:
            u = User(
                email=wd["email"],
                phone=wd["phone"],
                password_hash=get_password_hash("worker123"),
                role=UserRole.WORKER,
                is_verified=True
            )
            db.add(u)
            await db.flush()

            wp = WorkerProfile(
                user_id=u.id,
                full_name=wd["name"],
                phone=wd["phone"],
                bio=wd["bio"],
                latitude=wd["lat"],
                longitude=wd["lng"],
                service_radius_km=15.0,
                availability_status=wd["status"],
                trust_score=82.0,
                verification_status=wd["verification"]
            )
            db.add(wp)
            await db.flush()
            worker_objs.append(wp)

            for sk in wd["skills"]:
                wsk = WorkerSkill(
                    worker_id=wp.id,
                    skill_name=sk["name"],
                    years_experience=sk["exp"],
                    hourly_rate=sk["rate"],
                    skill_tags=sk["tags"]
                )
                db.add(wsk)

        # 3. Job Provider Users & Profiles
        providers_data = [
            {"email": "priya.sharma@gmail.com", "name": "Priya Sharma", "phone": "+919876511111", "lat": 12.9716, "lng": 77.5946},
            {"email": "vimal.tech@gmail.com", "name": "Vimal Kumar", "phone": "+919876522222", "lat": 12.9352, "lng": 77.6245}
        ]

        provider_objs = []
        for pd in providers_data:
            u = User(
                email=pd["email"],
                phone=pd["phone"],
                password_hash=get_password_hash("provider123"),
                role=UserRole.PROVIDER,
                is_verified=True
            )
            db.add(u)
            await db.flush()

            pp = ProviderProfile(
                user_id=u.id,
                full_name=pd["name"],
                phone=pd["phone"],
                default_latitude=pd["lat"],
                default_longitude=pd["lng"]
            )
            db.add(pp)
            await db.flush()
            provider_objs.append(pp)

        await db.commit()

        # 4. Path A: Posted Jobs
        j1 = Job(
            provider_id=provider_objs[0].id,
            title="Urgent Kitchen Sink & Pipe Leak Repair",
            description="Major water leakage under the kitchen sink in MG Road flat. Need an experienced plumber immediately.",
            required_skill="Plumbing",
            budget_min=400.0,
            budget_max=700.0,
            latitude=12.9716,
            longitude=77.5946,
            urgency=JobUrgency.IMMEDIATE,
            source=JobSource.POSTED,
            status=JobStatus.OPEN
        )
        j2 = Job(
            provider_id=provider_objs[1].id,
            title="Complete 3BHK Apartment Rewiring Check & MCB Setup",
            description="Need licensed electrician to inspect main distribution board and replace faulty MCB switches in Koramangala.",
            required_skill="Electrical Wiring",
            budget_min=1000.0,
            budget_max=1800.0,
            latitude=12.9352,
            longitude=77.6245,
            urgency=JobUrgency.SCHEDULED,
            scheduled_date="2026-08-20",
            source=JobSource.POSTED,
            status=JobStatus.OPEN
        )
        db.add(j1)
        db.add(j2)
        await db.commit()

        # 5. Path B: Direct Offer
        o1 = DirectOffer(
            provider_id=provider_objs[0].id,
            worker_id=worker_objs[2].id, # Manjunath driver
            title="Outstation Weekend Driver to Mysore",
            description="Looking for an experienced driver for a 2-day family trip to Mysore in Innova Crysta.",
            required_skill="Personal Driving",
            proposed_budget=2500.0,
            latitude=12.9716,
            longitude=77.5946,
            scheduled_date="2026-08-22",
            status=DirectOfferStatus.PENDING
        )
        db.add(o1)
        await db.commit()

        # 6. Compute initial trust scores for all workers
        for wp in worker_objs:
            await compute_and_update_trust_score(wp.id, db)

        # 7. Run initial Isolation Forest fraud model
        await run_isolation_forest_fraud_detection(db)

        print("Database seeded successfully with Path A jobs, Path B offers, workers, and ML computations!")

if __name__ == "__main__":
    asyncio.run(seed_database())
