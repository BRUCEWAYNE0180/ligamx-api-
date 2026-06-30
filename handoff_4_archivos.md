# Handoff 4: Detalles tecnicos archivo por archivo

## app/main.py
- Crea app FastAPI
- Carga .env con load_dotenv()
- Configura CORS (allow_credentials=false, allow_origins=["*"])
- Registra todos los routers
- Scheduler desactivado en web service (RUN_SCHEDULER=false)

## app/dependencies.py
- verify_api_key: lee SYNC_API_KEY de os.environ en cada request
- get_or_404: helper para buscar por ID

## app/database.py
- Engine, SessionLocal, Base
- SQLite local por defecto, PostgreSQL en produccion

## app/models.py
- Stadium, Team, Season, Week, Match, Player, Standing, TopScorer, News, MatchStat, PlayerStat
- NUEVO: Match.sofascore_event_id
- NUEVO: MatchEvent, MatchLineup (tablas vacias, aun no se sincronizan)

## app/schemas.py
- Response models para todos los endpoints
- NUEVO: MatchEventResponse, MatchLineupResponse
- MatchBase ahora incluye sofascore_event_id

## app/routers/
- health.py: /, /health
- teams.py: endpoints de equipos + search + last-matches
- matches.py: endpoints de partidos + upcoming + sofascore
- standings.py: standings + top-scorers
- stadiums.py: estadios
- players.py: jugadores + top
- stats.py: player-stats
- news.py: noticias
- sync.py: POST /sync
- sofascore.py: endpoints de SofaScore directos

## app/scrapers/
- espn_requests_scraper.py: scraper principal de ESPN
- sofascore_scraper.py: scraper de SofaScore (SEASON_ID=96191 para 2026)
- news_scraper.py: noticias de Flashscore con Playwright
- sync_all_stats.py: stats avanzados de ESPN
- factory.py: registro de scrapers

## app/services/sync_service.py
- run_sync: sincronizacion completa
- calculate_week_numbers: calculo de jornadas
- _sync_sofascore_event_ids: encuentra y guarda sofascore_event_id para cada partido
- _teams_match: helper para comparar nombres de equipos ESPN vs SofaScore

## sync.py
- Script CLI que usa sync_service.run_sync()
- Corre en GitHub Actions cada 6 horas

## render.yaml
- Web service + PostgreSQL
- buildCommand incluye playwright install chromium
- SYNC_API_KEY placeholder (cambiar en dashboard)
- PLAYWRIGHT_BROWSERS_PATH=0

## .github/workflows/sync.yml
- Corre sync.py cada 6 horas
- Necesita secret DATABASE_URL apuntando a Render PostgreSQL
