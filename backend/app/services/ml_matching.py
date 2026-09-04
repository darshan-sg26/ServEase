import math
import re
from typing import List, Dict, Any, Tuple

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates Haversine distance in kilometers between two lat/lng coordinates.
    Earth radius R = 6371.0 km.
    """
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

# Dictionary of skill aliases and related keyword tokens for domain relevance checking
SKILL_ALIASES = {
    "plumbing": {"plumb", "plumber", "leak", "pipe", "drain", "sink", "sanitary", "faucet", "tap", "flush", "water", "toilet"},
    "electrical": {"electr", "electrician", "wire", "wiring", "mcb", "switch", "circuit", "short", "plug", "socket", "light", "fan"},
    "driving": {"drive", "driver", "cab", "car", "vehicle", "innova", "outstation", "chauffeur", "trip"},
    "cooking": {"cook", "cooking", "chef", "food", "kitchen", "meal", "cuisine", "catering"},
    "housekeeping": {"housekeeping", "clean", "maid", "dusting", "sweeping", "mopping"},
    "carpentry": {"carpenter", "carpentry", "wood", "furniture", "door", "cabinet", "shelf"},
}

def check_skill_relevance(job_skill: str, job_title: str, worker_skills: List[Dict[str, Any]]) -> Tuple[bool, float]:
    """
    Strict Skill Eligibility Gate.
    Verifies if a worker possesses at least one skill or tag matching the job skill requirement.
    """
    req_text = f"{job_skill} {job_title}".lower()
    
    # Extract worker skill tokens
    worker_tokens = set()
    for s in worker_skills:
        name = s.get("skill_name", "").lower()
        worker_tokens.update(re.findall(r'\w+', name))
        for tag in s.get("skill_tags", []):
            worker_tokens.update(re.findall(r'\w+', tag.lower()))

    # 1. Direct word overlap check
    req_words = set(re.findall(r'\w+', req_text)) - {"the", "a", "an", "and", "or", "for", "in", "to", "of", "with"}
    overlap = req_words.intersection(worker_tokens)
    if overlap:
        return True, max(0.5, len(overlap) / max(1, len(req_words)))

    # 2. Domain alias check
    for domain, keywords in SKILL_ALIASES.items():
        if any(kw in req_text for kw in keywords):
            # Job is in this domain. Check if worker has any keyword in this domain
            if any(kw in token for token in worker_tokens for kw in keywords):
                return True, 0.60

    # 3. Partial substring match check
    for req_w in req_words:
        if len(req_w) >= 4:
            for w_tok in worker_tokens:
                if len(w_tok) >= 4 and (req_w in w_tok or w_tok in req_w):
                    return True, 0.50

    return False, 0.0

def rank_workers_for_job(
    job_title: str,
    job_description: str,
    job_skill: str,
    job_lat: float,
    job_lng: float,
    workers_data: List[Dict[str, Any]],
    search_radius_km: float = 15.0,
) -> List[Dict[str, Any]]:
    """
    Hybrid ML Job Matching Algorithm with Strict Skill Relevance Gate and Dual Radius Constraints:
    - Worker service radius (worker's operational boundary)
    - Job search radius (provider's targeted search boundary)
    Calculates match_score = Skill_Gate * (0.50*content_score + 0.25*geo_score + 0.15*trust_factor + 0.10*behavioral)
    """
    ranked = []

    for worker in workers_data:
        w_lat = worker.get("latitude")
        w_lng = worker.get("longitude")
        if w_lat is None or w_lng is None:
            # Skip workers with no location set
            continue

        worker_radius = worker.get("service_radius_km", 15.0) or 15.0
        effective_radius = min(worker_radius, search_radius_km) if search_radius_km and search_radius_km > 0 else worker_radius

        # Step 1: Geospatial filter (Haversine radius)
        dist_km = calculate_haversine_distance(job_lat, job_lng, w_lat, w_lng)
        if dist_km > effective_radius:
            continue

        # Step 2: Strict Skill Relevance Gate
        worker_skills = worker.get("skills", [])
        is_relevant, skill_content_score = check_skill_relevance(job_skill, job_title, worker_skills)
        if not is_relevant:
            # HARD GATE: Worker has zero skills in this domain
            continue

        # Step 3: Normalized Geo Score (closer = higher score, 0-1)
        geo_score = max(0.0, 1.0 - (dist_km / effective_radius))

        # Step 4: Behavioral Score
        completion_rate = worker.get("completion_rate", 0.90)
        acceptance_rate = worker.get("acceptance_rate", 0.85)
        behavioral_score = (completion_rate + acceptance_rate) / 2.0

        # Step 5: Trust Score factor (0 - 1)
        trust_factor = min(1.0, max(0.0, worker.get("trust_score", 75.0) / 100.0))

        # Weighted Match Score Computation
        match_score = (
            0.50 * skill_content_score +
            0.25 * geo_score +
            0.15 * trust_factor +
            0.10 * behavioral_score
        )

        final_percentage = round(match_score * 100.0, 2)
        if final_percentage >= 30.0:
            ranked.append({
                "worker_profile": worker["profile_obj"],
                "match_score": final_percentage,
                "distance_km": round(dist_km, 2),
                "content_score": round(skill_content_score, 2),
                "geo_score": round(geo_score, 2),
                "behavioral_score": round(behavioral_score, 2),
                "trust_score_factor": round(trust_factor, 2)
            })

    # Sort descending by match score
    ranked.sort(key=lambda x: x["match_score"], reverse=True)
    return ranked
