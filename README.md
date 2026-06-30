# Liga MX API

API REST de Liga MX con datos de equipos, jugadores, partidos, jornadas, standings, estadisticas y noticias.

## Stack
- Python 3.11
- FastAPI + Uvicorn
- SQLAlchemy 2.x + Pydantic
- SQLite local / PostgreSQL en Render

## Variables de entorno
Copia .env.example a .env y llena SYNC_API_KEY.

## Instalacion
pip install -r requirements.txt

## Sincronizar datos
python sync.py

## Correr la API
python -m uvicorn app.main:app --reload

## Endpoints principales
GET /health
GET /teams
GET /matches
GET /matches/week/{week}
GET /standings
GET /players
GET /top-scorers
GET /news
POST /sync
