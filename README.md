# Liga MX API ⚽🇲🇽

API REST de la **Liga MX (Torneo Apertura 2026)** construida con **FastAPI**.
Reúne datos de **múltiples fuentes públicas** (no solo ESPN) y los sirve de forma
estructurada: equipos, jugadores, partidos, tabla de posiciones, goleadores,
estadísticas, alineaciones, eventos en vivo, noticias y más.

---

## 🔌 Fuentes de datos

| Fuente | Uso | Estado |
|--------|-----|--------|
| **ESPN** (`site.api.espn.com`) | Equipos, escudos, plantillas, estadios, partidos, tabla, goleadores y estadísticas | ✅ Fuente principal del sync |
| **365Scores** (`webws.365scores.com`) | Fixtures/resultados frescos del Apertura, tabla, alineaciones con posiciones, eventos (goles/tarjetas/cambios) | ✅ Datos en vivo, no bloqueado |
| **TheSportsDB** | Año de fundación, capacidad de estadios, escudos/jerseys (cruce por `idESPN`), **highlights en video + miniaturas** y calendario | ✅ Enriquecimiento + media |
| **Google Noticias / ESPN (RSS)** | Noticias de Liga MX en español | ✅ Vía `feedparser` |
| **SofaScore** | Detalle de partidos / incidencias | ⚠️ Bloqueado por Cloudflare (403) desde servidores; endpoints quedan como *best-effort* |

---

## 🚀 Puesta en marcha local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # ajusta tus variables
uvicorn app.main:app --reload
```

Documentación interactiva (Swagger): **http://localhost:8000/docs**

### Cargar datos

```bash
# Opción A: script directo (usa ESPN)
python sync.py

# Opción B: endpoint protegido por API key
curl -X POST "http://localhost:8000/sync?source=espn" -H "X-API-Key: $SYNC_API_KEY"
```

Fuentes válidas para `source`: `espn` (recomendada), `365scores`, `demo` (datos de prueba sin red).

### Variables de entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `DATABASE_URL` | URL de la BD. SQLite local o PostgreSQL en producción | `sqlite:///./ligamx.db` |
| `SYNC_API_KEY` | Clave requerida para `POST /sync` | — |
| `RUN_SCHEDULER` | Si `true`, el web service corre el sync cada 6h | `false` |

> El esquema `postgres://` se normaliza automáticamente a `postgresql://`.

---

## 🧬 Migraciones de base de datos (Alembic)

El esquema de la base de datos se gestiona con **Alembic**.

```bash
# Aplicar todas las migraciones (crea/actualiza tablas)
alembic upgrade head

# Tras cambiar los modelos en app/models.py, generar una migración nueva
alembic revision --autogenerate -m "describe el cambio"
```

- En **desarrollo con SQLite**, la app crea las tablas automáticamente al
  arrancar (no necesitas correr Alembic).
- En **producción con PostgreSQL**, el esquema lo maneja Alembic. El despliegue
  en Render ejecuta `alembic upgrade head` antes de iniciar, y el workflow de
  sincronización también lo corre antes de cargar datos. Esto resuelve el
  *drift* de esquema: las columnas/tablas nuevas se aplican a bases existentes.

---

## 📚 Catálogo de endpoints

### General
- `GET /` — info de la API
- `GET /health` — health check
- `GET /season` — **torneo vigente y datos cargados** (Apertura/Clausura, si ya inició, total de partidos) 🆕

### Equipos
- `GET /teams` — lista (paginada) con escudo, fundación y estadio
- `GET /teams/search?q=` — búsqueda por nombre (ignora acentos)
- `GET /teams/{id}` — detalle
- `GET /teams/{id}/players` — plantilla
- `GET /teams/{id}/last-matches` — últimos partidos
- `GET /teams/{id}/form` — **forma reciente** (W/D/L + racha) 🆕
- `GET /teams/{id}/stats?season=` — promedios/totales de estadísticas

### Partidos
- `GET /matches` — filtros: `team_id`, `week`, `status`, `limit`, `offset`
- `GET /matches/upcoming` — próximos partidos
- `GET /matches/team/{team_id}` — por equipo
- `GET /matches/week/{n}` — por jornada
- `GET /matches/{id}` — detalle
- `GET /matches/{id}/timeline` — **línea de tiempo guardada**: goles, tarjetas y cambios 🆕
- `GET /matches/{id}/squad` — **alineaciones guardadas** (titulares/suplentes, posición, dorsal) 🆕
- `GET /matches/{id}/full` — **TODO el partido en una respuesta** (marcador, eventos, alineaciones, stats) 🆕
- `GET /matches/{id}/live` — **marcador EN VIVO** (goles, reloj, periodo, estado) 🆕
- `GET /matches/{id}/stats` — estadísticas del partido (ESPN)
- `GET /matches/{id}/lineups` — alineaciones (ESPN)
- `GET /matches/{id}/events` — eventos clave (goles/tarjetas/cambios)
- `GET /matches/{id}/cards` — solo tarjetas
- `GET /matches/{id}/player-stats` — **stats completas por jugador del partido, guardadas en BD** (minutos, goles, xG, xA, pases, regates, rating...) 🆕
- `GET /matches/live` — partidos en vivo (hoy)
- `GET /matches/today?date=YYYY-MM-DD` — partidos de un día
- `GET /h2h/{team1}/{team2}` — historial entre dos equipos
- `GET /h2h/{team1}/{team2}/summary` — **resumen del historial** (victorias, goles, empates) 🆕
- `GET /weeks` — jornadas disponibles
- `GET /weeks/current` — jornada actual

### Tabla y goleadores
- `GET /standings` — tabla de posiciones
- `GET /liguilla` — **clasificación a Liguilla / Play-In** (formato Liga MX) 🆕
- `GET /top-scorers?season=` — tabla de goleo

### Jugadores y estadísticas
- `GET /players` — lista
- `GET /players/search?q=&position=&nationality=&team_id=` — **búsqueda y filtros** (ignora acentos) 🆕
- `GET /players/top?season=` — mejores por goles
- `GET /players/{id}` — detalle
- `GET /players/{id}/stats?season=` — estadísticas del jugador
- `GET /players/{id}/match-stats?season=` — **historial partido a partido** con stats completas 🆕
- `GET /players/{id}/season-stats?season=` — **resumen agregado de la temporada** (minutos, goles, asistencias, xG, xA, rating promedio) 🆕
- `GET /players/season-leaders?stat=&season=&min_appearances=` — **tabla de líderes desde la BD** (goals, assists, minutes, xg, xa, rating...) 🆕
- `GET /player-stats?season=` — estadísticas agregadas

### Datos en vivo (365Scores)
- `GET /365scores/matches?week=&status=` — fixtures/resultados frescos
- `GET /365scores/standings` — tabla
- `GET /365scores/teams` — equipos
- `GET /365scores/matches/{game_id}/info` — **ficha del partido: sede, árbitro y cuerpo arbitral** 🆕
- `GET /365scores/matches/{game_id}/lineups` — alineaciones con posiciones
- `GET /365scores/matches/{game_id}/events` — eventos
- `GET /365scores/matches/{game_id}/cards` — tarjetas
- `GET /365scores/matches/{game_id}/player-stats` — **estadísticas COMPLETAS por jugador** (minutos, goles, xG, xA, remates, pases, regates, duelos, intercepciones, rating...) para todos los jugadores 🆕
- `GET /365scores/leaders?category_id=` — **líderes de temporada por jugador** en 16 categorías (goles, asistencias, xG, tarjetas, salvadas, valla invicta...) 🆕
- `GET /365scores/team-leaders?category_id=` — líderes de temporada por equipo 🆕

### Extras
- `GET /extras/highlights` — highlights en **video + miniaturas** de los últimos partidos (TheSportsDB, con Scorebat de respaldo)
- `GET /extras/calendar` — **próximos partidos** con miniatura, sede y horario (TheSportsDB) 🆕
- `GET /extras/teams/assets` — escudos/jerseys/estadios (TheSportsDB)
- `GET /extras/teams/{espn_team_id}/assets` — assets de un equipo

### Noticias
- `GET /news` — noticias de Liga MX (RSS, en español)

### Sincronización
- `POST /sync?source=espn` — recarga los datos (requiere header `X-API-Key`)
- `GET /sync/status` — **estado y frescura de los datos** (último sync, si fue exitoso, antigüedad) 🆕

---

## 🗓️ Sincronización automática

El sync programado corre vía **GitHub Actions** (`.github/workflows/sync.yml`)
cada 6 horas, ejecutando `python sync.py` contra la BD de producción
(`secrets.DATABASE_URL`). Alternativamente, puedes activar `RUN_SCHEDULER=true`
en el web service para que sea él quien sincronice.

---

## ☁️ Despliegue en Render

El archivo `render.yaml` define el web service + base de datos PostgreSQL.
Recuerda definir `SYNC_API_KEY` en el dashboard (no se versiona en el repo).

```
buildCommand: pip install -r requirements.txt
startCommand: uvicorn app.main:app --host 0.0.0.0 --port 10000
```

---

## ⚡ Rendimiento (caché)

Los endpoints que consultan fuentes externas (`/matches/live`, `/matches/today`,
`/matches/{id}/stats|lineups|events|cards`, todos los `/365scores/*` y
`/extras/*`) usan un **caché en memoria con TTL** (de 30s para datos en vivo
hasta 24h para assets). Esto responde al instante y evita rate-limits/baneos de
las fuentes. Los endpoints que leen de la base de datos no se cachean (ya son
rápidos).

---

## 🧪 Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

La suite cubre el helper de temporada, el caché, la red de seguridad del sync y
los endpoints principales (con una BD SQLite sembrada, sin tocar la red).
Se ejecuta automáticamente en cada push/PR vía GitHub Actions
(`.github/workflows/tests.yml`), que además valida que las migraciones de
Alembic apliquen correctamente.

---

```
app/
├── main.py            # App FastAPI + routers + scheduler opcional
├── database.py        # Engine SQLAlchemy (Postgres/SQLite)
├── models.py          # Modelos ORM
├── schemas.py         # Esquemas Pydantic (respuestas)
├── dependencies.py    # API key + helpers
├── routers/           # Endpoints por dominio
├── scrapers/          # Un scraper por fuente (patrón BaseScraper + factory)
└── services/
    └── sync_service.py  # Orquestación del sync (FETCH → WRITE → ENRICH)
alembic/                 # Migraciones de base de datos
└── versions/            # Scripts de migración generados
```

El **sync** es seguro por diseño: primero descarga todo a memoria (FETCH); si una
fuente crítica falla, **aborta sin tocar la BD**. La escritura ocurre en una sola
transacción (WRITE) y el enriquecimiento (stats, assets, noticias) corre aislado
(ENRICH), de modo que un fallo ahí no invalida el resto.

### Qué se guarda en la base de datos

Equipos, estadios, jugadores, temporada, jornadas, partidos, tabla de posiciones,
goleadores, estadísticas por equipo y por jugador, noticias y, por cada partido
jugado, su **línea de tiempo completa** (goles, **tarjetas amarillas y rojas**,
cambios) y sus **alineaciones** (titulares y suplentes con posición y dorsal).
El marcador en vivo se consulta en el momento a la fuente (con caché corto).
