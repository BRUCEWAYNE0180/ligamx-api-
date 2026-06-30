#!/usr/bin/env python
"""Kit de recuperacion de la base de datos (Liga MX API).

Pensado para cuando caduca la base PostgreSQL del plan free de Render (~30 dias):
creas una base nueva, defines DATABASE_URL y corres ESTE script. En un solo
comando deja la API lista: verifica la conexion, aplica las migraciones y
sincroniza todos los datos de la temporada vigente.

Uso (desde la raiz del repo):

    export DATABASE_URL="postgresql://...."   # la nueva base
    python scripts/recover.py                 # temporada vigente (ESPN)
    python scripts/recover.py --source espn   # fuente explicita
    python scripts/recover.py --skip-migrate  # si ya migraste

No necesita SYNC_API_KEY: llama al sync directamente (la API key solo protege
el endpoint HTTP /sync, no esta funcion interna).
"""
import argparse
import os
import sys
import time

# Asegura que el paquete `app` sea importable al ejecutar desde la raiz.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _fail(msg: str, code: int = 1):
    print(f"\n❌ {msg}")
    sys.exit(code)


def main() -> None:
    parser = argparse.ArgumentParser(description="Recupera/inicializa la base de datos de la Liga MX API")
    parser.add_argument("--source", default="espn", help="Fuente de datos (espn | 365scores | demo)")
    parser.add_argument("--skip-migrate", action="store_true", help="No correr 'alembic upgrade head'")
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url or db_url.startswith("sqlite"):
        _fail("Define DATABASE_URL con la base destino antes de correr el script.\n"
              '   Ej: export DATABASE_URL="postgresql://usuario:pass@host/db"')

    # Oculta credenciales al imprimir.
    safe = db_url
    if "@" in safe:
        safe = safe.split("@", 1)[0].split("//", 1)[0] + "//***@" + safe.split("@", 1)[1]
    print(f"🎯 Base destino: {safe}")

    # 1) Verifica conexion.
    from sqlalchemy import text
    from app.database import engine
    print("🔌 Probando conexion...", end=" ", flush=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("OK ✅")
    except Exception as e:
        _fail(f"No se pudo conectar a la base: {e}")

    # 2) Migraciones (alembic upgrade head).
    if not args.skip_migrate:
        print("📦 Aplicando migraciones (alembic upgrade head)...")
        try:
            from alembic import command
            from alembic.config import Config
            command.upgrade(Config("alembic.ini"), "head")
            print("   Migraciones aplicadas ✅")
        except Exception as e:
            _fail(f"Fallaron las migraciones: {e}")

    # 3) Sync de datos.
    print(f"🔄 Sincronizando datos (source={args.source})... esto puede tardar 1-3 min.")
    started = time.time()
    from app.database import SessionLocal
    from app.services.sync_service import run_sync_with_log
    db = SessionLocal()
    try:
        result = run_sync_with_log(db, args.source)
    except Exception as e:
        _fail(f"El sync fallo: {e}")
    finally:
        db.close()

    elapsed = time.time() - started
    print("\n✅ RECUPERACION COMPLETA")
    print(f"   Temporada: {result.get('season')}")
    print(f"   Equipos:   {result.get('teams')}")
    print(f"   Jugadores: {result.get('players')}")
    print(f"   Partidos:  {result.get('matches')}")
    print(f"   Tiempo:    {elapsed:.0f}s")
    print("\n👉 La API ya tiene datos. Verifica con: GET /sync/status y GET /standings")


if __name__ == "__main__":
    main()
