"""Backfill de temporadas PASADAS de Liga MX (operativo, no destructivo).

Corre `run_backfill_with_log` para cada temporada indicada y al final imprime una
verificacion: todas las temporadas cargadas con su numero de partidos y el total,
para confirmar que la nueva quedo y que NO se borraron las demas.

Las temporadas se toman de la variable de entorno SEASONS, como lista separada
por comas en formato `anio:torneo`, p. ej.:

    SEASONS="2025:Clausura,2024:Apertura,2024:Clausura,2023:Apertura"

Regla dura: no se fabrica nada. Si ESPN no tiene una temporada (0 partidos), se
salta y se reporta como "skipped" sin abortar el resto.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base, SessionLocal  # noqa: E402
from app.services.sync_service import run_backfill_with_log  # noqa: E402
from app import models  # noqa: E402

# Set por defecto: los torneos pasados solicitados (hacia atras desde 2025).
DEFAULT_SEASONS = "2025:Clausura,2024:Apertura,2024:Clausura,2023:Apertura"


def _parse_seasons(raw: str):
    out = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            year_s, tournament = chunk.split(":", 1)
            out.append((int(year_s.strip()), tournament.strip().capitalize()))
        except ValueError:
            print(f"AVISO: '{chunk}' no tiene formato anio:torneo; se ignora")
    return out


def main():
    # En SQLite (dev) creamos tablas al vuelo; en Postgres el esquema lo maneja
    # Alembic (el workflow corre `scripts/migrate.py` antes que este script).
    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(bind=engine)

    seasons = _parse_seasons(os.getenv("SEASONS", DEFAULT_SEASONS))
    if not seasons:
        print("No hay temporadas que cargar (SEASONS vacio).")
        return 0

    db = SessionLocal()
    loaded, skipped, errored = [], [], []
    try:
        for year, tournament in seasons:
            label = f"{tournament} {year}"
            print(f"\n=== Backfill {label} ===")
            try:
                res = run_backfill_with_log(db, year, tournament, "espn")
                print(f"OK {res['season']}: {res['matches']} partidos "
                      f"({res['finished_matches']} jugados), tabla {res['standings_rows']} equipos")
                loaded.append(res["season"])
            except ValueError as e:
                # ESPN no tiene esa temporada (0 partidos) u otro dato faltante:
                # se salta sin fabricar y sin abortar el resto.
                print(f"SKIP {label}: {e}")
                skipped.append(label)
            except Exception as e:  # noqa: BLE001
                db.rollback()
                print(f"ERROR {label}: {e}")
                errored.append(label)

        # -------- Verificacion final (equivalente a GET /seasons) --------
        print("\n===== VERIFICACION: temporadas en la BD =====")
        all_seasons = (db.query(models.Season)
                       .order_by(models.Season.year.desc(), models.Season.name.desc()).all())
        total_matches = 0
        for s in all_seasons:
            n = db.query(models.Match).filter(models.Match.season_id == s.id).count()
            total_matches += n
            print(f"  - {s.name}: {n} partidos")
        print(f"TOTAL: {len(all_seasons)} temporadas, {total_matches} partidos")
        print(f"\nResumen -> cargadas: {loaded or '-'} | saltadas: {skipped or '-'} | "
              f"errores: {errored or '-'}")
    finally:
        db.close()

    # Falla el job solo si hubo un error real (no por temporadas ausentes en ESPN).
    return 1 if errored else 0


if __name__ == "__main__":
    sys.exit(main())
