# Estado del proyecto — Liga MX API

> Documento único de estado. Reemplaza a los antiguos `handoff_1..5.md`
> (estaban desactualizados: mencionaban Playwright/Flashscore y SofaScore como
> "funcionando", cosas que ya no aplican). Para el catálogo de endpoints y la
> guía de uso, ver el `README.md`.

## Stack
- Python 3.11 · FastAPI + Uvicorn · SQLAlchemy 2.x · Pydantic v2
- SQLite en local / PostgreSQL en Render
- Migraciones con **Alembic** (`alembic upgrade head` corre en el arranque de Render y antes del sync)
- APScheduler opcional (`RUN_SCHEDULER`), normalmente apagado: el sync lo dispara GitHub Actions

## Fuentes de datos (vigentes)
| Fuente | Uso | Estado |
|--------|-----|--------|
| **ESPN** | Equipos, jugadores, estadios, partidos, tabla, stats, eventos, alineaciones | ✅ Principal |
| **365Scores** | Fixtures en vivo, tabla, alineaciones, eventos, ficha (sede/árbitro) | ✅ No bloqueado |
| **TheSportsDB** | Fundación, capacidad de estadios, escudos, highlights, calendario | ✅ Enriquecimiento |
| **RSS (Google News / ESPN)** | Noticias en español (`feedparser`) | ✅ |
| **SofaScore** | Detalle de partidos (best-effort) | ⚠️ Bloqueado por Cloudflare desde el server |

> Nota: la antigua dependencia de **Playwright/Chromium** para noticias de
> Flashscore fue eliminada; ahora las noticias salen de RSS.

## Arquitectura del sync (FETCH → WRITE → ENRICH)
1. **FETCH**: descarga todo a memoria. Si una fuente crítica falla, **aborta sin tocar la BD**.
2. **WRITE**: borrado + inserción en una sola transacción (rollback ante error).
3. **ENRICH** (aislado, no crítico): assets de TheSportsDB, stats avanzados,
   IDs de SofaScore, eventos/alineaciones por partido y noticias.

Una red de seguridad (`_validate_season`) aborta el sync si el torneo/año
detectado en los datos no coincide con el esperado.

## Variables de entorno
- `DATABASE_URL` — SQLite local o PostgreSQL en prod (`postgres://` se normaliza)
- `SYNC_API_KEY` — clave para `POST /sync`
- `RUN_SCHEDULER` — `true`/`false`
- `EXPECTED_SEASON_YEAR` / `EXPECTED_TOURNAMENT` — fuerzan la validación de temporada (casos borde)

## Roadmap pendiente

### Seguridad (prioridad alta)
- [x] `verify_api_key` endurecida: comparación de tiempo constante + `503` si el
      servidor no tiene `SYNC_API_KEY`. Rate limiting por IP activo.
- [ ] **Rotar `SYNC_API_KEY` en Render** (no usar valores de prueba en producción) — acción de operación.
- [ ] Validar que el sync de GitHub Actions apunte al `DATABASE_URL` correcto.

### Datos completos (el objetivo "todo por jugador")
- [x] **Estadísticas por jugador completas** vía 365Scores (líderes de temporada
      en 16 categorías + stats completas por jugador en cada partido).
- [x] Persistir **árbitros** (`Match.referee`, cruce con 365Scores).
- [x] **Streaming en vivo (SSE)**: `GET /live/stream` empuja marcadores en vivo
      sin polling.
- [ ] Lesionados/suspendidos y disponibilidad por jornada.
- [x] **Liguilla/Play-In**: `GET /liguilla/bracket` arma el cuadro oficial
      sembrado por la tabla (Play-In 7º-10º + Cuartos 1v8/2v7/3v6/4v5, a ida y
      vuelta; semis/final con resiembra por posición).
- [ ] Resultados reales por serie de Liguilla (las fuentes no exponen el bracket
      con marcadores de forma estable; se podría capturar los partidos de playoff
      por `stageName` de 365Scores en una iteración futura).
- [x] **Histórico multi-temporada**: el sync ya NO borra todo: hace *upsert* de
      equipos/jugadores/estadios y reemplaza solo la temporada sincronizada, así
      se acumulan torneos. `GET /seasons` lista los disponibles y casi todos los
      endpoints aceptan `?season=` (etiqueta o año). Clave de temporada =
      etiqueta completa ("Apertura 2026") para no mezclar los dos torneos del año.
- [x] **Backfill de temporadas pasadas**: `POST /sync/backfill?year=&tournament=`
      carga un torneo pasado (ESPN da los partidos por rango de fechas) y
      reconstruye su tabla desde los resultados. No destructivo.
- [ ] Histórico multi-temporada consultable por endpoint.
- [x] Persistir las stats por jugador del partido en BD (`player_match_stats`),
      con agregados de temporada (`/players/{id}/season-stats`), historial
      (`/players/{id}/match-stats`) y tabla de líderes (`/players/season-leaders`).

### Plataforma
- [x] Búsqueda global (`GET /search?q=`) sobre equipos, jugadores y estadios.
- [x] **Streaming en vivo (SSE)**: `GET /live/stream` empuja marcadores en vivo
      sin polling (Server-Sent Events).
- [x] **Rate limiting por IP** (slowapi): límite global configurable + límite
      estricto en `/sync` y `/sync/backfill`. Cabeceras `X-RateLimit-*` y `429`.
- [x] **Seguridad endurecida**: `verify_api_key` con comparación de tiempo
      constante y `503` si falta `SYNC_API_KEY`; cabeceras `X-Content-Type-Options`,
      `X-Frame-Options`, `Referrer-Policy`.
- [x] **Redis opcional** para caché compartido entre workers (`REDIS_URL`); con
      fallback transparente al caché en proceso si Redis no está o no conecta.
- [x] **Observabilidad**: logging de acceso (método, ruta, status, ms) y métricas
      en proceso en `GET /metrics` (uptime, requests por código, latencias, top rutas, caché).
- [x] **Versionado de API**: todas las rutas existen en la raíz (`/...`, legado) y
      bajo `/v1/...` (recomendado). `GET /version` lista las versiones.

## Hecho recientemente
- **Analítica**: comparador de jugadores (`/compare/players`) y equipos
  (`/compare/teams`), y predictor de partidos (`/predict`, modelo Poisson con
  fuerzas de ataque/defensa + ventaja de local).
- xG por **equipo** (`/teams/xg-performance`), **tabla de porteros**
  (`/365scores/goalkeepers`) y **heatmaps por jugador**
  (`/365scores/matches/{id}/heatmaps`).
- Noticias **unificadas** en `/news`: RSS (Google/ESPN) + feed propio de 365Scores,
  con miniatura (`image_url`). (Nota: el scraping de Flashscore se retiró hace
  tiempo por frágil/pesado; se reemplazó por RSS.)
- `GET /calendar`: calendario por jornada con rival, sede oficial y marcador.
- `GET /365scores/news`: noticias de Liga MX (feed propio de 365Scores).
- `GET /players/xg-performance`: rendimiento goles vs xG (sobre/bajo-rendimiento).
- Capturas del calendario sacadas del control de versiones (queda el PDF oficial).
- Estadios con nombres **oficiales del Apertura 2026** (calendario LIGA BBVA):
  Azteca → **Estadio Banorte** (América) y Alfonso Lastras → **Estadio Libertad
  Financiera** (Atlético de San Luis).
- Stats por jugador **persistidas en BD** (`player_match_stats`): historial
  partido a partido, agregados de temporada y tabla de líderes, todo cruzando con
  365Scores en una sola pasada del sync (un request por partido, que también trae
  el árbitro).
- Estadísticas por jugador completas vía 365Scores: líderes de temporada en 16
  categorías (`/365scores/leaders`), líderes por equipo (`/365scores/team-leaders`)
  y stats completas por jugador del partido (`/365scores/matches/{id}/player-stats`:
  minutos, xG, xA, pases, regates, duelos, intercepciones, rating...).
- Árbitros: `Match.referee` se puebla en el sync (cruce con 365Scores) y se expone
  en `/matches/{id}/full`.
- Migración a Pydantic v2 (`ConfigDict`).
- Limpieza de scrapers muertos (`top_scorers_scraper`, `player_stats_scraper`,
  `sync_player_stats`) y del shim `fetch_flashscore_news`.
- Soporte de **Clausura** en el scraper de ESPN (antes solo bajaba Apertura).
- `Match.stadium_id` ahora se puebla y la sede se expone en `/matches/{id}/full`.
- Las rutas `/matches/{id}/stats|lineups|events|cards` usan el **id interno**
  del partido (antes mezclaban el id externo de ESPN).
- `MatchStat` guarda métricas extra (offsides, atajadas, pases, tackles, etc.).
- Eliminada la tabla muerta `weeks` (se usa `week_number`).
