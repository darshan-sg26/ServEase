import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '../../backend/servease.db')

def run_db_audit():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    counts = {}
    for t in tables:
        cursor.execute(f"SELECT count(*) FROM {t}")
        counts[t] = cursor.fetchone()[0]

    # Coordinate check
    cursor.execute("SELECT count(*) FROM worker_profiles WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
    workers_with_coords = cursor.fetchone()[0]

    cursor.execute("SELECT count(*) FROM jobs WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
    jobs_with_coords = cursor.fetchone()[0]

    # Skills check
    cursor.execute("SELECT count(DISTINCT worker_id) FROM worker_skills")
    workers_with_skills = cursor.fetchone()[0]

    cursor.execute("SELECT count(*) FROM jobs WHERE required_skill IS NOT NULL AND trim(required_skill) != ''")
    jobs_with_skills = cursor.fetchone()[0]

    # Interactions
    cursor.execute("SELECT status, count(*) FROM job_applications GROUP BY status")
    apps_by_status = dict(cursor.fetchall())

    cursor.execute("SELECT status, count(*) FROM direct_offers GROUP BY status")
    offers_by_status = dict(cursor.fetchall())

    audit_summary = {
        "tables": counts,
        "worker_profiles_with_coords": workers_with_coords,
        "jobs_with_coords": jobs_with_coords,
        "workers_with_skills_in_relational_table": workers_with_skills,
        "jobs_with_skills": jobs_with_skills,
        "job_applications_by_status": apps_by_status,
        "direct_offers_by_status": offers_by_status,
    }

    conn.close()
    return audit_summary

if __name__ == "__main__":
    summary = run_db_audit()
    print(json.dumps(summary, indent=2))
