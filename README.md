# MosquitoWatch NYC

MosquitoWatch NYC is a public-health surveillance dashboard that predicts elevated West Nile-positive mosquito activity by area and week, using historical NYC Health surveillance data combined with weather and seasonality signals. Gemini explains why the model flags an area as high or low risk. The product predicts elevated *mosquito/surveillance* activity — not individual human infection risk.

## Architecture

```
data/raw  →  data/processed  →  ML training  →  FastAPI  →  Gemini  →  React
```

1. **Data** cleans and joins surveillance + weather into `data/processed/training_data.csv`
2. **ML** trains a model and writes artifacts to `ml/artifacts/`
3. **FastAPI** loads those artifacts and serves JSON over HTTP
4. **Gemini** generates plain-language explanations of model outputs
5. **React** (Vite) renders the dashboard from the API

## Folder structure

```
mosquito-watch/
├── backend/
│   ├── app.py
│   ├── schemas.py
│   ├── config.py
│   ├── data_service.py
│   ├── model_service.py
│   ├── gemini_service.py
│   ├── artifacts/
│   ├── tests/
│   └── requirements.txt
│
├── frontend/          (Vite app, scaffolded separately)
│
├── data/
│   ├── raw/
│   └── processed/
│
├── ml/
│   ├── notebooks/
│   └── artifacts/
│
├── README.md
├── DATA_TASKS.md
├── ML_TASKS.md
├── BACKEND_TASKS.md
├── FRONTEND_TASKS.md
└── .gitignore
```

## Setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then set GEMINI_API_KEY
uvicorn app:app --reload --port 8000
```

Health check: [http://localhost:8000/health](http://localhost:8000/health)

### Frontend

*Placeholder — frontend will be scaffolded separately with Vite.*
