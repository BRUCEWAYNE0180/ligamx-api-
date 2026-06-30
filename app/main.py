from dotenv import load_dotenv
load_dotenv()

import os
import re
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import subprocess

from app.database import engine, Base
from app import models
from app.rate_limit import limiter
from app.routers import health, teams, matches, standings, stadiums, players, stats, news, sync, sofascore, scores365, extras, search, live

# En desarrollo (SQLite) creamos las tablas automaticamente para arrancar sin
# pasos extra. En produccion (PostgreSQL) el esquema lo gestiona Alembic
# (`alembic upgrade head`), que SI maneja cambios de columnas/migraciones.
if engine.dialect.name == "sqlite":
    Base.metadata.create_all(bind=engine)

scheduler = BackgroundScheduler()

def auto_sync():
    python = sys.executable
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    subprocess.run([python, "sync.py"], cwd=project_root)

if os.getenv("RUN_SCHEDULER", "false").lower() == "true":
    scheduler.add_job(auto_sync, "interval", hours=6)
    scheduler.start()

def _unique_route_id(route) -> str:
    """operationId unico por ruta (necesario porque cada router se monta dos
    veces: en la raiz y bajo /v1, lo que produciria ids duplicados)."""
    return re.sub(r"[^0-9a-zA-Z_]", "_", f"{route.name}_{route.path}").strip("_")


app = FastAPI(title="Liga MX API", version="1.0", generate_unique_id_function=_unique_route_id)

# Rate limiting por IP (slowapi). El limite por defecto aplica a todas las rutas;
# los endpoints sensibles (sync) anaden un limite mas estricto.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def security_headers(request, call_next):
    """Cabeceras de seguridad basicas para una API publica."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Todos los routers se montan DOS veces: en la raiz (retrocompatibilidad con los
# clientes actuales) y bajo el prefijo /v1 (version estable para evolucionar sin
# romper a nadie). Asi, p. ej., /standings y /v1/standings devuelven lo mismo.
ROUTERS = [
    health.router, teams.router, matches.router, standings.router, stadiums.router,
    players.router, stats.router, news.router, sync.router, sofascore.router,
    scores365.router, extras.router, search.router, live.router,
]

for _r in ROUTERS:
    app.include_router(_r)
for _r in ROUTERS:
    app.include_router(_r, prefix="/v1")


@app.get("/version", tags=["meta"])
def api_version():
    """Versiones de la API disponibles. Las rutas existen en la raiz (legado) y
    bajo /v1 (recomendado para nuevos clientes)."""
    return {
        "api": "Liga MX API",
        "version": "1.0",
        "available_versions": ["v1"],
        "current": "v1",
        "note": "Las rutas estan disponibles en la raiz (/...) y bajo /v1 (/v1/...).",
    }
