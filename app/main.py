from dotenv import load_dotenv
load_dotenv()

import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
import subprocess

from app.database import engine, Base
from app import models
from app.routers import health, teams, matches, standings, stadiums, players, stats, news, sync, sofascore, scores365, extras

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

app = FastAPI(title="Liga MX API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(teams.router)
app.include_router(matches.router)
app.include_router(standings.router)
app.include_router(stadiums.router)
app.include_router(players.router)
app.include_router(stats.router)
app.include_router(news.router)
app.include_router(sync.router)
app.include_router(sofascore.router)
app.include_router(scores365.router)
app.include_router(extras.router)
