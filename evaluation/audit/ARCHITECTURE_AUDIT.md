# Architecture Audit: Presentation Architecture vs Code Reality

This document validates every architectural component claimed in the ServEase project presentation (`Digital-Trust-and-Intelligent-Job-Matching-Platform-for-Informal-Workforce.pptx`, Slide 6 & 7) against actual repository files and runtime paths.

---

## 1. System Architecture Validation Table

| Presentation Component | Actual File / Service in Repo | Used at Runtime? | Engineering Status | Empirical Evidence / Code Reference |
|---|---|:---:|---|---|
| **Worker Mobile App** | `mobile_app/lib/screens/worker/worker_shell.dart` | **Yes** | **VERIFIED** | Full Flutter UI with feed, nearby jobs, applications, direct offers, completed jobs, and GPS updates. |
| **Provider Mobile App** | `mobile_app/lib/screens/provider/provider_shell.dart` | **Yes** | **VERIFIED** | Full Flutter UI with job posting, worker browse, ML matches modal, direct outreach, and applicant review. |
| **Admin Shell / Dashboard** | `mobile_app/lib/screens/admin/admin_shell.dart`<br>`backend/app/api/v1/admin.py` | **Yes** | **VERIFIED** | Flags review, verification status management, and audit inspection. |
| **Interactive Map Discovery** | `mobile_app/lib/screens/map/map_discovery_screen.dart` | **Yes** | **VERIFIED** | `flutter_map` OpenStreetMap view displaying nearby workers/jobs with server-computed Haversine distance. |
| **API Gateway / Router** | `backend/app/main.py`<br>`backend/app/api/v1/` | **Yes** | **VERIFIED** | FastAPI REST routing with CORS, exception handlers, and Pydantic validation. |
| **Authentication Service** | `backend/app/api/v1/auth.py`<br>`backend/app/core/security.py` | **Yes** | **VERIFIED** | JWT bearer authentication, bcrypt hashing, OTP verification via Gmail API, and Google Sign-In verification. |
| **Skill-Based Matching** | `backend/app/services/ml_matching.py` | **Yes** | **PARTIALLY VERIFIED** | Implemented as rule-based token/alias overlap rather than TF-IDF vector space embeddings. |
| **Dynamic Trust Scoring** | `backend/app/services/trust_engine.py` | **Yes** | **VERIFIED** | Bayesian rating smoothing with volume weighting; logged to `trust_score_log`. |
| **Geospatial Optimization** | `backend/app/services/ml_matching.py`<br>`backend/app/api/v1/jobs.py` | **Yes** | **VERIFIED** | Exact Haversine distance calculation and dual radius filtering ($d \le \min(\text{service\_radius}, \text{search\_radius})$). |
| **Fraud Detection Engine** | `backend/app/services/fraud_engine.py` | **Yes** | **PARTIALLY VERIFIED** | Scikit-learn `IsolationForest(contamination=0.1)` flags outliers to `fraud_flags`. Lacks supervised classification and labeled fraud data. |
| **Relational Database** | `backend/app/core/database.py`<br>`backend/app/models/domain.py` | **Yes** | **VERIFIED** | Dual mode: Local SQLite (`backend/servease.db`) and Cloud PostgreSQL (`NeonDB`). |
| **External Email / OTP** | `backend/app/services/email_service.py` | **Yes** | **VERIFIED** | Direct Google OAuth2 Gmail API integration on port 443 for OTP delivery. |
| **External Google Auth** | `backend/app/api/v1/auth.py` | **Yes** | **VERIFIED** | Google token verification via Google OAuth2 libraries. |

---

## 2. Detailed Component Inspection

### 2.1 Mobile Application Tier (Flutter)
- The mobile application is a production Flutter application compiled and deployed for Android (`servease.apk`, 54.8 MB).
- Contains distinct role workflows for **Worker**, **Provider**, and **Admin**.
- Features reactive state management, offline-safe error handling, and GPS location synchronization with the backend.
- UI elements connect directly to the FastAPI REST backend via `ApiService`.

### 2.2 Server Tier (FastAPI)
- Uses asynchronous SQLAlchemy with `AsyncSession`.
- Routes are cleanly partitioned into:
  - `/api/v1/auth`: Login, registration, OTP send/verify, Google auth, profile retrieval.
  - `/api/v1/workers`: Worker listing, search, location update, availability toggle.
  - `/api/v1/jobs`: Job creation, detail, radius search, ML matches, applications, lifecycle state transitions.
  - `/api/v1/direct_offers`: Provider direct outreach workflow to specific workers.
  - `/api/v1/admin`: Administrative metrics and fraud flag reviews.

### 2.3 Data Tier
- Relational schema defined in `backend/app/models/domain.py` containing 11 tables:
  `users`, `worker_profiles`, `provider_profiles`, `worker_skills`, `jobs`, `job_applications`, `direct_offers`, `reviews`, `fraud_flags`, `trust_score_log`, `pending_registrations`.
- Integrity constraints, foreign keys, timestamps, and geolocation coordinates are properly indexed and stored.

### 2.4 Conceptual vs Actual Distinctions
1. **"TF-IDF Vector Space Skill Matching"**:
   - Presentation Slide 2 & 6 claim: *"Combines TF-IDF-based skill matching with geospatial allocation"*.
   - Reality in code: No `TfidfVectorizer` or cosine vector computation existed in `ml_matching.py`. The actual implementation used string set intersection and 6 dictionary alias lists.
2. **"Supervised Fraud Classifier"**:
   - Presentation Slide 7 claims: *"0.85 – 0.90 Fraud Detection AUC"*.
   - Reality in code: Scikit-learn `IsolationForest` unsupervised clustering on 5 features. Because no ground truth fraud labels exist, AUC cannot be measured.
