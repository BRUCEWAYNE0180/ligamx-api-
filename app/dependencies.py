import os
from fastapi import Header, HTTPException
from sqlalchemy import case
from app import models


def verify_api_key(api_key: str = Header(..., alias="X-API-Key")):
    sync_api_key = os.environ.get("SYNC_API_KEY")
    if api_key != sync_api_key:
        raise HTTPException(status_code=403, detail="API Key invalida")
    return api_key

def get_or_404(db, model, id_value):
    item = db.query(model).filter(model.id == id_value).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    return item


def _apertura_first():
    # Dentro de un mismo ano, el Apertura es posterior al Clausura.
    return case((models.Season.tournament_type == "Apertura", 1), else_=0)


def latest_season(db):
    """Temporada mas reciente cargada (ano desc, y dentro del ano Apertura > Clausura)."""
    return db.query(models.Season).order_by(models.Season.year.desc(), _apertura_first().desc()).first()


def find_season(db, season=None):
    """Resuelve una temporada por etiqueta exacta ('Apertura 2026'), por ano
    ('2026' -> torneo mas reciente de ese ano) o, si no se indica, la vigente."""
    if not season:
        return latest_season(db)
    s = db.query(models.Season).filter(models.Season.name == season).first()
    if s is None and str(season).isdigit():
        s = (db.query(models.Season)
             .filter(models.Season.year == int(season))
             .order_by(_apertura_first().desc())
             .first())
    return s


def resolve_season_id(db, season=None):
    """id de temporada para filtrar matches/standings. -1 si se pidio una
    temporada inexistente (-> resultados vacios); None si no hay temporadas."""
    s = find_season(db, season)
    if s:
        return s.id
    return -1 if season else None


def resolve_season_label(db, season=None):
    """Etiqueta de temporada (clave de las tablas de stats: 'Apertura 2026')."""
    from app.season import current_season_name
    s = find_season(db, season)
    if s:
        return s.name
    return season or current_season_name()
