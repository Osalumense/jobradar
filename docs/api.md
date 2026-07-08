# API Reference — JobRadar AI

This document specifies the REST API endpoints exposed by the JobRadar backend (`services/scorer`). All endpoints are relative to the backend base URL (default: `http://localhost:9089`).

---

## 1. Authentication Endpoints

These endpoints manage user session and registration state. Session details are persisted securely using HTTP-only cookies (`access_token` and `refresh_token`).

### Register User
* **Endpoint**: `POST /api/auth/register`
* **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "strongpassword123"
  }
  ```
* **Response (200 OK)**:
  ```json
  {
    "message": "User registered successfully",
    "user_id": "uuid-string"
  }
  ```

### Log In
* **Endpoint**: `POST /api/auth/login`
* **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "strongpassword123"
  }
  ```
* **Response (200 OK)**: Sets HTTP-only cookies.
  ```json
  {
    "message": "Login successful"
  }
  ```

### Log Out
* **Endpoint**: `POST /api/auth/logout`
* **Response (200 OK)**: Clears cookies.
  ```json
  {
    "message": "Logout successful"
  }
  ```

### Get Current User Profile Info
* **Endpoint**: `GET /api/auth/me`
* **Headers**: Requires active session cookies.
* **Response (200 OK)**:
  ```json
  {
    "user_id": "uuid-string",
    "email": "user@example.com"
  }
  ```

### Forgot Password (Request Token)
* **Endpoint**: `POST /api/auth/forgot-password`
* **Request Body**:
  ```json
  {
    "email": "user@example.com"
  }
  ```

### Reset Password (Use Token)
* **Endpoint**: `POST /api/auth/reset-password`
* **Request Body**:
  ```json
  {
    "token": "reset-token-received-via-email",
    "new_password": "newpassword123"
  }
  ```

---

## 2. Profile and Resume Ingestion

Configure user profile, parsing CV content, and managing target matching criteria.

### Parse CV Text via Gemini
* **Endpoint**: `POST /api/profile/parse-cv`
* **Body Form-Data**:
  - `file`: PDF or Word file (upload)
* **Response (200 OK)**:
  ```json
  {
    "text": "Extracted CV content string...",
    "skills": ["Python", "Docker", "Node.js"]
  }
  ```

### Get Matching Profile Criteria
* **Endpoint**: `GET /api/profile`
* **Response (200 OK)**:
  ```json
  {
    "full_name": "John Doe",
    "email": "john@doe.com",
    "target_roles": ["Backend Developer", "DevOps Engineer"],
    "target_tech": ["Python", "FastAPI", "Docker"],
    "target_contracts": ["CDI", "Alternance"],
    "target_locations": ["Paris", "Remote"]
  }
  ```

### Update Matching Profile Criteria
* **Endpoint**: `POST /api/profile`
* **Request Body**:
  ```json
  {
    "full_name": "John Doe",
    "email": "john@doe.com",
    "phone": "+336000000",
    "github_url": "https://github.com/...",
    "linkedin_url": "https://linkedin.com/in/...",
    "master_cv": "Entire text block of CV for Gemini context...",
    "target_roles": ["Backend Developer"],
    "target_tech": ["Python", "Nuxt"],
    "target_contracts": ["CDI"],
    "target_locations": ["Paris"]
  }
  ```

---

## 3. Scrapers & Job Board Controls

Trigger scans and recalculate scores.

### Trigger Scraper Search
* **Endpoint**: `POST /api/scrape`
* **Description**: Initiates automated parallel scraping across Welcome to the Jungle, HelloWork, France Travail, LesJeudis, and Remotive based on the collective query criteria in user profiles.
* **Response (200 OK)**:
  ```json
  {
    "status": "triggered",
    "details": "Scrape jobs successfully scheduled in background"
  }
  ```

### Recalculate Scoring Weights (Rescore)
* **Endpoint**: `POST /api/rescore`
* **Query Parameters**:
  - `limit`: (Optional) Maximum number of recent jobs to rescore. Default: 100.
* **Description**: Redownloads/computes embeddings and re-matches keywords for all stored jobs. Useful if the user modifies target tech stack or upload a new CV.

---

## 4. Job Retrieval & AI Operations

### Get Job Feed (Sorted/Filtered)
* **Endpoint**: `GET /api/jobs`
* **Query Parameters**:
  - `limit`: Default 20
  - `offset`: Default 0
  - `contract_type`: Filter by CDI, CDD, Alternance, Stage
  - `source`: Filter by scraping source (e.g. `wttj`)
  - `min_score`: Minimum composite score (0 to 1)
* **Response (200 OK)**:
  ```json
  {
    "total": 142,
    "limit": 20,
    "offset": 0,
    "jobs": [
      {
        "id": "job-uuid",
        "title": "Backend Python Developer",
        "company": "AI Labs",
        "location": "Paris",
        "contract_type": "CDI",
        "url": "https://...",
        "scraped_at": "2026-07-08T12:00:00Z",
        "score": {
          "composite": 0.85,
          "semantic": 0.91,
          "keyword": 0.80,
          "recency": 0.95
        }
      }
    ]
  }
  ```

### Suggest Relevant Accomplishment Vault Feats
* **Endpoint**: `POST /api/jobs/{job_id}/suggest-feats`
* **Description**: Analyzes the target job requirements using Google Gemini and selects the top matching accomplishments from the vault.

### Generate AI Application Materials (CV/Cover Letter)
* **Endpoint**: `POST /api/jobs/{job_id}/materials`
* **Request Body**:
  ```json
  {
    "selected_feat_ids": ["feat-uuid-1", "feat-uuid-2"],
    "application_questions": "Why do you want to join us?"
  }
  ```
* **Response (200 OK)**:
  ```json
  {
    "cover_letter_markdown": "Tailored cover letter in French structure...",
    "resume_adjustments_markdown": "Targeted suggestions to align your CV..."
  }
  ```
