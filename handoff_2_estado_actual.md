# Handoff 2: Estado actual - que funciona

## Sincronizacion
- sync.py y POST /sync hacen exactamente lo mismo
- Usan app/services/sync_service.py
- Sincronizan: equipos, jugadores, estadios, partidos, standings, stats, noticias
- Temporada dinamica (2026 actualmente)
- Jornadas calculadas por fecha (viernes-jueves)

## Datos actuales
- Temporada 2026 de Liga MX Apertura
- 18 equipos, 17 estadios, ~389 jugadores, 153 partidos
- Partidos: del 17 de julio al 23 de noviembre 2026
- Status: todos scheduled (la temporada no ha iniciado)

## Endpoints funcionando
- /, /health
- /teams, /teams/{id}, /teams/{id}/players, /teams/{id}/stats, /teams/search, /teams/{id}/last-matches
- /matches, /matches/{id}, /matches/upcoming, /matches/team/{id}, /matches/week/{week}, /h2h/{t1}/{t2}, /matches/today, /matches/live, /matches/{id}/stats, /matches/{id}/sofascore
- /weeks, /weeks/current
- /standings
- /stadiums
- /players, /players/{id}, /players/{id}/stats, /players/top
- /top-scorers
- /news
- /player-stats
- /sofascore/matches, /sofascore/matches/{id}, /sofascore/matches/{id}/incidents, /sofascore/matches/{id}/lineups, /sofascore/player-stats
- POST /sync

## Integraciones externas
- ESPN: funciona correctamente
- Flashscore: noticias en vivo funcionan
- SofaScore: endpoints de partidos, incidentes, alineaciones, stats funcionan

## Produccion
- Deploy en Render: https://ligamx-api.onrender.com
- GitHub Actions sincroniza cada 6 horas
- SYNC_API_KEY actual: test123 (INSEGURO, cambiar)
