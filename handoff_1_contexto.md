# Handoff 1: Contexto general de ligamx-api

## Que es
API REST de Liga MX que expone datos de equipos, jugadores, partidos, jornadas, standings, estadisticas, goleadores y noticias en vivo.

## Stack tecnologico
- Python 3.11
- FastAPI + Uvicorn
- SQLAlchemy 2.x + Pydantic
- SQLite local / PostgreSQL en Render
- APScheduler (opcional, desactivado en web service)
- Playwright (para noticias de Flashscore y posible scraping)
- Render para deploy

## Fuentes de datos
1. ESPN (principal): equipos, jugadores, partidos, standings, stats
2. Flashscore: noticias en vivo
3. SofaScore: detalles de partidos, incidentes, alineaciones, stats de jugadores
4. DemoScraper: datos hardcodeados para pruebas

## Variables de entorno
- DATABASE_URL: sqlite:///./ligamx.db (local) o PostgreSQL en produccion
- SYNC_API_KEY: clave para POST /sync
- RUN_SCHEDULER: true/false, controla scheduler en main.py

## Deploy actual
- Web service en Render: https://ligamx-api.onrender.com
- Cron job NO en Render (se usa GitHub Actions)
- GitHub Actions corre sync.py cada 6 horas
- Base de datos PostgreSQL en Render

## Estado del deploy
- Deploy verde en Render
- SYNC_API_KEY actual en produccion: test123 (INSEGURO, debe cambiarse)
- Produccion aun tiene datos viejos (2025) hasta que se fuerce un nuevo sync

## Archivos clave
- app/main.py: App FastAPI, CORS, routers
- app/services/sync_service.py: Logica de sincronizacion
- app/scrapers/espn_requests_scraper.py: Datos de ESPN
- app/scrapers/sofascore_scraper.py: Datos de SofaScore
- app/scrapers/news_scraper.py: Noticias de Flashscore
- app/models.py: Modelos de base de datos
- app/routers/: Endpoints
- sync.py: Script CLI
- render.yaml: Config de Render
