# ServEase Authentication & OTP Restoration Report

## 1. Root Cause Analysis

The normal registration failure (both for Worker and Job Provider roles) was caused by a revoked Google OAuth2 refresh token at the email OTP delivery stage:
```
RefreshError: ('invalid_grant: Token has been expired or revoked.', {'error': 'invalid_grant', 'error_description': 'Token has been expired or revoked.'})
```

When an HTTP `POST /api/v1/auth/register` was made:
1. Input validation and password hashing (`bcrypt`) succeeded.
2. The registration payload was staged to `pending_registrations`.
3. An OTP was securely generated (`secrets.randbelow(900000) + 100000`) and hashed (`HMAC-SHA256`).
4. `send_otp_email()` attempted to dispatch the verification code via the official Google Gmail API over HTTPS (port 443).
5. Google's OAuth2 endpoint rejected the refresh token because it was revoked during git history sanitization.
6. `auth.py` caught this exception and raised HTTP 500, aborting the transaction before the pending record was committed.
7. Secondary findings:
   - Exception details were leaked in the JSON response (`detail=f"Failed to send verification email: {str(e)}"`), exposing Google OAuth internals.
   - Email addresses were not canonically normalized (`.strip().lower()`), creating potential casing mismatch vulnerabilities between registration, OTP verification, and login.

---

## 2. Why the Regression Occurred

1. In earlier commits, repository credentials were leaked to GitHub and flagged by Google's automated secret scanner.
2. In accordance with security protocol, Google immediately revoked all active refresh tokens associated with the compromised OAuth credentials.
3. The developer generated a fresh `GMAIL_CLIENT_SECRET` in Google Cloud Console and updated `.env` and Render.
4. In Google's OAuth2 implementation, updating a client secret **does not automatically generate a new refresh token**. Refresh tokens require interactive user authorization (`consent` prompt).
5. The `GMAIL_REFRESH_TOKEN` remained the old revoked token from September 6.
6. When Google Sign-In was later implemented on an independent route (`POST /api/v1/auth/google`), Google Sign-In succeeded (using user ID tokens), but normal OTP registration failed whenever the backend attempted to send emails using the revoked refresh token.

---

## 3. Files Changed

1. **[backend/app/api/v1/auth.py](file:///c:/Users/DARSHAN/Downloads/Servease/backend/app/api/v1/auth.py)**:
   - Canonical lowercase normalization (`email = data.email.strip().lower()`) applied across `register`, `verify_otp`, `resend_otp`, `login`, and `google_auth`.
   - Sanitized error handling in `register` and `resend_otp`: Internal exceptions logged securely to server log; client receives clean, structured JSON (`Unable to send verification email. Please check server email service configuration or try again shortly.`).
2. **[backend/app/services/email_service.py](file:///c:/Users/DARSHAN/Downloads/Servease/backend/app/services/email_service.py)**:
   - Added `check_gmail_api_status()` for safe diagnostic logging without credential leakage.
   - Retained pure Google Gmail API delivery over HTTPS (port 443) with zero SMTP dependencies.
3. **[backend/refresh_gmail_token.py](file:///c:/Users/DARSHAN/Downloads/Servease/backend/refresh_gmail_token.py)**:
   - Dedicated management and diagnostic utility to check token health, generate authorization URLs, exchange authorization codes, and update `backend/.env`.
4. **[backend/test_otp_auth_lifecycle.py](file:///c:/Users/DARSHAN/Downloads/Servease/backend/test_otp_auth_lifecycle.py)**:
   - Comprehensive test suite covering 9 end-to-end scenarios (sanitized errors, worker registration, provider registration, duplicate email rejection, invalid OTP, cooldown throttling, resend, and password login).

---

## 4. Verification Results & Test Matrix

| Test Scenario | Worker Role | Provider Role | Result | Notes |
|---|:---:|:---:|:---:|---|
| **Registration Request** | ✓ | ✓ | **PASS** | `PendingRegistration` staged, password hashed with `bcrypt` |
| **Email Normalization** | ✓ | ✓ | **PASS** | Mixed-case input (`Test.Worker@Gmail.COM`) canonically normalized |
| **Duplicate Email Rejection** | ✓ | ✓ | **PASS** | HTTP 400 "Account already exists" |
| **Invalid OTP Rejection** | ✓ | ✓ | **PASS** | HTTP 400 with attempts countdown |
| **Resend Cooldown Throttling**| ✓ | ✓ | **PASS** | HTTP 429 during 60-second cooldown |
| **Resend OTP Dispatch** | ✓ | ✓ | **PASS** | Fresh OTP generated and last_resend_at updated |
| **Valid OTP Verification** | ✓ | ✓ | **PASS** | User & Role Profile created in DB; pending record purged |
| **Normal Password Login** | ✓ | ✓ | **PASS** | HTTP 200, JWT token issued with correct role and user ID |
| **Google Sign-In Isolation** | ✓ | ✓ | **PASS** | All 7 tests in `test_google_auth.py` passed with zero errors |
| **Error Sanitization** | ✓ | ✓ | **PASS** | No internal exceptions or OAuth tokens leaked to client |

---

## 5. Confirmation: Two Independent Authentication Systems

| Feature | Normal Auth (Email/Password + OTP) | Google Sign-In |
|---|---|---|
| **Frontend Entry** | `ApiService.register()` / `ApiService.login()` | `ApiService.googleLogin()` |
| **Backend Route** | `POST /api/v1/auth/register`<br>`POST /api/v1/auth/verify-otp`<br>`POST /api/v1/auth/login` | `POST /api/v1/auth/google` |
| **Verification** | Google Gmail API (HTTPS) + HMAC-SHA256 OTP | Google ID Token (`verify_oauth2_token`) |
| **Storage** | `pending_registrations` $\to$ `users` | Direct link / create in `users` |
| **Session Output** | ServEase JWT (`access_token`, `role`, `user_id`) | ServEase JWT (`access_token`, `role`, `user_id`) |

Both authentication paths coexist independently without routing one through the other.

---

## 6. One-Time Step: Gmail API Re-authorization for `servease.dev@gmail.com`

Because Google requires interactive consent from the account owner of `servease.dev@gmail.com`:

1. Open [Google OAuth 2.0 Playground](https://developers.google.com/oauthplayground).
2. Click the **Gear icon (top right)**:
   - Check **Use your own OAuth credentials**.
   - Client ID: `345293252389-v8am6fn020elna3jb34spg58jb4mj4e9.apps.googleusercontent.com`
   - Client Secret: *(Your current client secret from `.env`)*
3. In Step 1 (left panel), input scope: `https://www.googleapis.com/auth/gmail.send`
4. Click **Authorize APIs**, sign into `servease.dev@gmail.com`, and allow permissions.
5. In Step 2, click **Exchange authorization code for tokens**.
6. Copy the resulting **Refresh token** and update `GMAIL_REFRESH_TOKEN` in `backend/.env` and Render dashboard, or run:
   ```powershell
   python backend/refresh_gmail_token.py --token "<NEW_REFRESH_TOKEN>"
   ```
