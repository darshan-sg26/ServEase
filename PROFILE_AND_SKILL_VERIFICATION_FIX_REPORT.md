# SERVEASE — PROFILE EDIT PERSISTENCE & SKILL VERIFICATION WORKFLOW AUDIT & FIX REPORT

## Executive Summary

- **PROFILE EDIT**:
  - **Before**: Worker clicked "Edit Profile Info", changed details (e.g. name, phone, bio, hourly rate), and clicked Update. The modal popped immediately, but errors were swallowed, the backend did not update linked `User.phone`, local state was not updated with the persisted server record, and background refresh dropped concurrent requests. Result: database remained unpersisted and UI reverted.
  - **After**: Worker updates their profile info; changes are verified, sanitized, and transactionally committed to PostgreSQL/NeonDB & SQLite across both `worker_profiles` and `users` tables. The server returns the updated database state. The Flutter modal handles loading and errors inline, updates local state directly upon success, shows feedback, and triggers a background refresh. Changes reflect immediately across all screens and storefronts.

- **SKILLS WORKFLOW**:
  - **Before**: Worker-added skills were unconditionally displayed with a hardcoded `VERIFIED` badge in the UI. No administrative review workflow existed, allowing any worker to instantly claim verified expertise.
  - **After**: Newly submitted worker skills are created with `PENDING` status. The worker storefront displays them with an amber `PENDING VERIFICATION` badge. Servease Admins inspect pending submissions in the dedicated **Skill Verification Queue** on the Admin Dashboard with worker trust scores and experience details. Admins can **Approve** (transitioning status to `VERIFIED`) or **Reject** (transitioning status to `REJECTED` with an optional reason). Only verified skills are matched in job candidate search and discovery.

---

## 1. Root Cause Analysis

### 1.1 Profile Edit Failure Root Cause
1. **Premature UI Dismissal (`Navigator.pop(ctx)`)**: In `worker_shell.dart`, `Navigator.pop(ctx)` was invoked synchronously *prior* to or concurrently with the asynchronous `ApiService.updateWorkerProfile` call. Users were given a visual indication of success before the HTTP request completed.
2. **Silent Failure Swallowing**: `ApiService.updateWorkerProfile` had a generic `try/catch` block that caught HTTP error responses (400, 422, 500) and simply returned `null` without throwing or returning error messages, completely masking backend rejections.
3. **Missing State Propagation & Dropped Background Reloads**: The modal dismissed without updating `_myProfile` with the response body. `_loadData()` had an `if (_isFetching) return;` guard that frequently dropped refresh calls if initial fetching was in flight.
4. **Desynchronized Phone Number Storage**: While worker name, bio, and hourly rate live in `WorkerProfile`, `phone` is also stored on the `User` entity. The backend route `PUT /api/v1/workers/me` previously only wrote to `profile.phone`, leaving `User.phone` unchanged and desynchronized.

### 1.2 Unverified Skill Auto-Verification Root Cause
1. **Hardcoded UI Tag**: `worker_shell.dart` previously hardcoded `const AppBadge(label: 'VERIFIED', variant: BadgeVariant.success)` for all skills in the storefront list.
2. **Missing Status Dimension in DB**: The `worker_skills` database table lacked a lifecycle status column (`status`), submission timestamp (`submitted_at`), review timestamp (`reviewed_at`), reviewer foreign key (`reviewed_by`), and rejection reason (`rejection_reason`).
3. **No Administrative Approval Gate**: The backend endpoint `POST /api/v1/workers/me/skills` merely inserted a raw skill name without review state or admin approval routes.

---

## 2. Files Changed

| Component | File Path | Description of Changes |
| :--- | :--- | :--- |
| **Backend Model** | `backend/app/models/domain.py` | Added `SkillStatus` enum (`pending`, `verified`, `rejected`), added `status`, `submitted_at`, `reviewed_at`, `reviewed_by` (FK to `users.id`), `rejection_reason`, `created_at`, `updated_at`, and reviewer relationship on `WorkerSkill`. |
| **Database Migration** | `backend/app/core/database.py` | Added safe backward-compatible SQLite & PostgreSQL migration logic in `init_db()`. Preserves existing legacy skills as `verified`. Creates composite indexes on `worker_skills` (`status`, `worker_id`, `reviewed_by`). |
| **Schemas** | `backend/app/schemas/domain.py` | Added `SkillStatus` enum, updated `WorkerSkillResponse` with review metadata, added `PendingSkillApprovalResponse` and `SkillRejectRequest`. |
| **Worker API** | `backend/app/api/v1/workers.py` | Partial update logic in `update_my_profile` commits to DB, updates `User.phone`, and returns refreshed profile. In `add_worker_skill`, checks duplicate verified/pending skills and defaults new skills to `SkillStatus.PENDING`. Filtered `list_nearby_workers` and `list_workers` to only match verified skills. |
| **Jobs API** | `backend/app/api/v1/jobs.py` | Filtered candidate matching queries so only workers with `status in ('verified', 'VERIFIED')` for the required skill receive skill match boosts. |
| **Admin API** | `backend/app/api/v1/admin.py` | Added `GET /api/v1/admin/skill-approvals`, `POST /api/v1/admin/skill-approvals/{skill_id}/approve`, and `POST /api/v1/admin/skill-approvals/{skill_id}/reject`. Guarded by `verify_admin` (strictly returns 403 Forbidden for non-admins). |
| **Flutter Models** | `mobile_app/lib/models/models.dart` | Added `status`, `submittedAt`, `reviewedAt`, `rejectionReason` to `WorkerSkill`. Added helpers `isVerified`, `isPending`, `isRejected`. Added `PendingSkillApproval` model for admin queues. |
| **Flutter API Service** | `mobile_app/lib/services/api_service.dart` | Refactored `updateWorkerProfile` and `addWorkerSkill` to return structured results `{success, profile, message}` with clear error feedback. Added `fetchPendingSkillApprovals()`, `approveSkill()`, and `rejectSkill()`. |
| **Flutter Worker Shell** | `mobile_app/lib/screens/worker/worker_shell.dart` | Updated storefront skill cards to render dynamic badges (`VERIFIED` green, `PENDING VERIFICATION` amber, `NOT APPROVED` red with reason). Fixed edit profile modal and add skill modal with stateful loading, inline error banners, and direct local state synchronization. |
| **Flutter Admin Shell** | `mobile_app/lib/screens/admin/admin_shell.dart` | Integrated "Skill Verification Queue" with pending count pill, worker cards, trust score badges, Approve button, and Reject button with optional rejection reason prompt. |
| **Automated Test Suite** | `backend/test_profile_and_skills.py` | Complete end-to-end test suite testing profile persistence, pending skills, admin approval/rejection, security enforcement, duplicate rejection, and discovery isolation. |

---

## 3. Database Schema Changes & Migration

### Schema Extension on `worker_skills`
```sql
ALTER TABLE worker_skills ADD COLUMN status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE worker_skills ADD COLUMN submitted_at TIMESTAMP;
ALTER TABLE worker_skills ADD COLUMN reviewed_at TIMESTAMP;
ALTER TABLE worker_skills ADD COLUMN reviewed_by INTEGER REFERENCES users(id);
ALTER TABLE worker_skills ADD COLUMN rejection_reason TEXT;
ALTER TABLE worker_skills ADD COLUMN created_at TIMESTAMP;
ALTER TABLE worker_skills ADD COLUMN updated_at TIMESTAMP;

CREATE INDEX idx_worker_skills_status ON worker_skills(status);
CREATE INDEX idx_worker_skills_worker_id ON worker_skills(worker_id);
CREATE INDEX idx_worker_skills_reviewed_by ON worker_skills(reviewed_by);
```

### Migration Safety & Legacy Data Preservation
- Implemented in `backend/app/core/database.py` inside `init_db()`.
- **Existing Legacy Skills**: During migration, any existing rows in `worker_skills` where `status IS NULL` are automatically updated to `status = 'verified'` and `submitted_at = CURRENT_TIMESTAMP`. Existing verified skills are never regressed.
- **SQLite Compatibility**: Executed column additions without non-constant defaults, followed by `UPDATE ... WHERE ... IS NULL` to ensure compatibility with SQLite engines.
- **PostgreSQL / NeonDB**: Schema introspections check `information_schema.columns` before altering table definitions to prevent redundant migration failures.

---

## 4. API Endpoints Contract

### Worker Profile
- `PUT /api/v1/workers/me`
  - **Auth**: Bearer token (Worker identity extracted from session).
  - **Payload**:
    ```json
    {
      "bio": "Experienced Electrician & Home Automation specialist",
      "hourly_rate": 450.0,
      "service_radius_km": 15.0,
      "phone": "+91 98765 43210"
    }
    ```
  - **Response**: HTTP 200 with full `WorkerProfileResponse`. Updates `User.phone` and `WorkerProfile`. Other fields (trust score, rating, completed jobs) are preserved.

### Worker Skills
- `POST /api/v1/workers/me/skills`
  - **Auth**: Bearer token (Worker identity).
  - **Payload**: `{"skill_name": "Carpentry", "years_experience": 4.0, "hourly_rate": 400.0}`
  - **Response**: HTTP 200 with `WorkerSkillResponse`:
    ```json
    {
      "id": 12,
      "skill_id": 12,
      "name": "Carpentry",
      "status": "pending",
      "years_experience": 4.0,
      "hourly_rate": 400.0,
      "submitted_at": "2026-09-23T16:55:00Z",
      "reviewed_at": null,
      "reviewed_by": null,
      "rejection_reason": null
    }
    ```
  - **Duplicate Handling**:
    - If already `VERIFIED`: Returns HTTP 400 `"This skill is already added and verified."`
    - If already `PENDING`: Returns HTTP 400 `"This skill is already pending verification."`

### Admin Skill Verification
- `GET /api/v1/admin/skill-approvals`
  - **Auth**: Admin only (`verify_admin`). Worker calling this receives HTTP 403 Forbidden.
  - **Response**: List of pending skill submissions with worker details, trust score, and experience.
- `POST /api/v1/admin/skill-approvals/{skill_id}/approve`
  - **Auth**: Admin only.
  - **Response**: `{"success": true, "status": "verified", "reviewed_at": "...", "reviewed_by": 1}`
- `POST /api/v1/admin/skill-approvals/{skill_id}/reject`
  - **Auth**: Admin only.
  - **Payload**: `{"reason": "Certificate document illegible."}`
  - **Response**: `{"success": true, "status": "rejected", "rejection_reason": "...", "reviewed_at": "..."}`

---

## 5. Flutter Client Enhancements

1. **Worker Storefront (`worker_shell.dart`)**:
   - Skills dynamically render according to `skill.status`:
     - `verified`: Green badge `VERIFIED` with checkmark.
     - `pending`: Amber badge `PENDING VERIFICATION` with clock icon.
     - `rejected`: Red badge `NOT APPROVED` with info icon, expandable rejection reason.
2. **Edit Profile Modal (`worker_shell.dart`)**:
   - Uses `StatefulBuilder` with an explicit loading state (`isSaving`).
   - Awaits `ApiService.updateWorkerProfile`.
   - On error: Displays an inline error alert within the modal without dismissing.
   - On success: Closes modal cleanly, updates `_myProfile` state directly with the server response, displays a green success SnackBar, and triggers a background refresh.
3. **Add Skill Modal (`worker_shell.dart`)**:
   - Uses `StatefulBuilder` with validation for skill name.
   - Awaits `ApiService.addWorkerSkill`.
   - Displays clear error if duplicate or invalid.
   - On success: Closes modal, displays an amber SnackBar `"Skill submitted! Pending Admin verification."`, and refreshes the worker's skill list.
4. **Admin Dashboard (`admin_shell.dart`)**:
   - Added **Skill Verification Queue** to the Monitoring Dashboard.
   - Displays badge counter of pending items.
   - Worker cards show name, category, years of experience, and worker trust score.
   - Quick **Approve** button (green) and **Reject** button (red with dialog for rejection reason).
   - Real-time removal of reviewed items from the pending list upon action.

---

## 6. Security and Authorization Rules

- **Server-Side Enforcement**: All admin endpoints verify the user's role via `verify_admin` dependency. Normal workers calling `GET /api/v1/admin/skill-approvals`, `/approve`, or `/reject` are strictly rejected with **HTTP 403 Forbidden**.
- **Worker Isolation**: In `PUT /api/v1/workers/me` and `POST /api/v1/workers/me/skills`, worker identity is strictly derived from the validated JWT token (`current_user.id`), preventing arbitrary impersonation.
- **Matching & Discovery Isolation**: Candidate ranking in `jobs.py` and nearby search in `workers.py` filter specifically for `WorkerSkill.status in ('verified', 'VERIFIED')`. Pending or rejected skills do not confer search boosts or matching recommendations.

---

## 7. Verification and Test Results

### 7.1 Automated End-to-End Suite (`test_profile_and_skills.py`)

| Test ID | Test Scenario | Expected Behavior | Result |
| :--- | :--- | :--- | :---: |
| **TEST A** | Worker Profile Edit & Database Persistence | Name, bio, phone persist to DB; `User.phone` updated; other fields unchanged. | **PASS** |
| **TEST B** | Worker Adds Skill | Skill added with `status=PENDING` and valid `submitted_at`. | **PASS** |
| **TEST C** | Admin Pending Approvals Queue | Admin retrieves pending skills with worker trust score and experience. | **PASS** |
| **TEST D** | Admin Approves Skill | Transition to `VERIFIED`; worker profile reflects verified status. | **PASS** |
| **TEST E** | Admin Rejects Skill with Reason | Transition to `REJECTED`; worker storefront displays rejection reason. | **PASS** |
| **TEST F** | Security Enforcement | Normal worker calling admin approval/rejection endpoints receives HTTP 403. | **PASS** |
| **TEST G** | Duplicate Skill Handling | Duplicate verified or pending skills rejected with HTTP 400. | **PASS** |
| **TEST H** | Matching & Search Isolation | Candidate matching algorithms only consider verified skills. | **PASS** |

### 7.2 Regression Verification Suite

| Test Suite | Purpose | Result |
| :--- | :--- | :---: |
| `flutter analyze mobile_app` | Static analysis of Flutter code for null-safety, async context guards, lints | **0 Issues (PASS)** |
| `python backend/test_google_auth.py` | Google Sign-In, token verification, account linking, invalid token rejection | **7/7 PASS** |
| `python backend/test_otp_auth_lifecycle.py` | Email/password registration, Gmail OTP delivery, cooldowns, verification, login | **9/9 PASS** |
| `python backend/test_location_and_matching.py` | Haversine distance, dual-radius matching, proximity calculations | **3/3 PASS** |
| `python backend/test_trust_and_ratings.py` | Cold-start trust scoring, Bayesian rating smoothing, two-way ratings | **9/9 PASS** |

---

## 8. Summary of Preserved Features

The following features were verified as completely intact with zero regressions:
1. **Google Sign-In & Google ID Token Verification**
2. **Normal Email + Password Registration & Login**
3. **Gmail API OTP Generation, Delivery, Cooldown & Verification**
4. **JWT Session Management & Role Enforcement**
5. **Job Creation, Browsing, Applications & Direct Hiring**
6. **Haversine Distance & Geospatial Proximity Matching**
7. **Bayesian Trust Scoring & Two-Way Rating System**
8. **Admin Dashboard Existing Stats, System Health & User Management**
