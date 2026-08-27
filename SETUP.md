# Setup

Run Redis, the FastAPI backend, and the Next.js frontend in three terminals from the repo root.

## Prerequisites

- Docker Desktop
- Python 3.11+ (3.14 works)
- Node.js 20+
- A Gemini API key

## 1. Redis Stack

Start this first. The chat semantic cache needs **Redis Stack** (RediSearch), not a plain Homebrew Redis.

```bash
docker compose up -d redis
docker compose ps
redis-cli -h 127.0.0.1 -p 6380 PING
```

You want `PONG`. Redis Stack is on **6380** so it does not collide with a local Redis on 6379.

Optional Redis Insight: [http://localhost:8001](http://localhost:8001)

Stop later with:

```bash
docker compose down
```

## 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` and set at least:

```bash
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.6-flash
```

The rest can stay as in `.env.example`:

```bash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSIONS=768
REDIS_URL=redis://localhost:6380
CACHE_MIN_SIMILARITY=0.95
```

Start the API:

```bash
uvicorn app:app --reload --port 8000
```

On startup you should see:

```text
INFO:     RAG Redis stack ready: semantic cache + forecast-grounded index
```

If you see `RAG Redis stack unavailable`, Redis is not reachable on 6380, or `REDIS_URL` is still pointing at Homebrew Redis on 6379.

Checks:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/chat/status
```

`/chat/status` should report `"redis_ready": true`.

Optional tests:

```bash
pytest
```

## 3. Frontend

In a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The app proxies `/backend/*` to `http://127.0.0.1:8000`.

## Quick smoke test

1. Map and ZIP lookup load live forecasts.
2. Open the green chat bubble (bottom left).
3. Ask: `which ZIP currently looks highest risk`
4. Ask the same idea in different words.

Backend logs:

```text
CACHE MISS stored=True redis=True ...
CACHE HIT similarity=0.97 ...
```

A miss with `redis=False` means the API never connected to Redis Stack. Restart Redis, confirm `REDIS_URL=redis://localhost:6380`, then restart uvicorn.
