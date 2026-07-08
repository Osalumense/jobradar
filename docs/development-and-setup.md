# Development & Setup Guide — JobRadar AI

This guide covers local environment setup, third-party credentials, running the stack (with Docker or bare-metal), seeding initial configurations, and common troubleshooting tips.

---

## 1. Prerequisites

Before starting, ensure you have:
- **Docker & Docker Compose** (Highly recommended)
- **Python 3.12+** (For bare-metal backend dev)
- **Node.js 18+** & **npm** (For bare-metal frontend dev)
- **Git**

---

## 2. API Keys & Credentials

JobRadar AI is powered by several external APIs. You will need to obtain the following before running:

### A. Neon Postgres DB (`DATABASE_URL`)
- Sign up for a free PostgreSQL database at [Neon.tech](https://neon.tech).
- Grab the connection string format: `postgresql://user:password@hostname/dbname?sslmode=require`.

### B. Google Gemini API (`GEMINI_API_KEY`)
- Get a free-tier API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
- This key embeds descriptions and generates cover letters.

### C. Upstash Redis (`UPSTASH_REDIS_REST_URL` & `UPSTASH_REDIS_REST_TOKEN`)
- Create a serverless Redis database at [Upstash](https://upstash.com).
- Copy the **REST URL** and **REST Token** from the dashboard. (JobRadar uses HTTP REST requests for lighter connection overhead).

### D. Resend Email (`RESEND_API_KEY`)
- Create an account on [Resend.com](https://resend.com) to send transactional emails.
- Copy your API key. (For dev, you can send emails to your own registered email address).

---

## 3. Quickstart with Docker Compose (Recommended)

Docker Compose is the fastest way to get the entire backend, worker, database configurations, and frontend running.

1. **Clone the repo:**
   ```bash
   git clone https://github.com/Osalumense/jobradar.git
   cd jobradar
   ```

2. **Configure Environment:**
   Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and paste all required API keys retrieved in Step 2.

3. **Start the Containers:**
   ```bash
   docker compose up --build
   ```
   This command starts:
   - **Backend API & worker** on `http://localhost:9089`
   - **Frontend App** on `http://localhost:3078`

---

## 4. Bare-Metal Development Setup

If you are modifying code and prefer faster hot-reloads, you can run the backend and frontend separately on your system.

### A. Backend Setup (`/services/scorer`)
1. Navigate to the backend directory:
   ```bash
   cd services/scorer
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy env variables (backend reads from the root `.env`):
   ```bash
   # Ensure you have .env configured at the root of the project
   ```
5. Run the FastAPI server:
   ```bash
   uvicorn main:app --reload --host 127.0.0.1 --port 9089
   ```

### B. Frontend Setup (`/frontend`)
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Run the Nuxt dev server:
   ```bash
   npm run dev -- --port 3078
   ```

---

## 5. Seeding the Database

To save you from manually filling in onboarding fields, CVs, and target tech queries, you can seed the database with a pre-configured profile.

1. Activate your backend virtual environment (or run it via docker).
2. Run the seeding script:
   ```bash
   cd services/scorer
   python run_onboarding_seed.py
   ```
3. This creates a user `akugbestephen3@gmail.com` (password: `testpassword123`) populated with:
   - A full markdown CV.
   - Target contracts: `Alternance`, `CDI`, `CDD`, `Stage`.
   - Target stack: `Python`, `Node.js`, `FastAPI`, `Nuxt`, `Docker`, `PostgreSQL`.
   - Pre-loaded search queries for scrapers.

---

## 6. Troubleshooting

- **CORS Errors**: The frontend app calls the backend on `http://localhost:9089`. Ensure the `SCORER_API_URL` environment variable is pointing to the correct backend host, and CORS origins configurations inside `services/scorer/main.py` allow your Nuxt port.
- **SSL Connection Errors**: Neon DB requires SSL. Ensure your `DATABASE_URL` ends with `?sslmode=require`. If using a local database without SSL, remove this parameter.
- **Gemini Rate Limit (429)**: The free tier of Gemini has a rate limit of 15 Requests Per Minute (RPM) for embeddings. If you queue a huge list of scrapers at once, the backend will serialize embedding calls but might hit the limit. Wait a minute and click **Rescore** to retry unscored jobs.
