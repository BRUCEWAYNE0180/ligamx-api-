#!/usr/bin/env python
"""Migracion self-healing (a prueba de resets parciales de la base).

Normalmente ejecuta `alembic upgrade head`. Pero el plan free se reinicia a
menudo y a veces la base queda con las TABLAS creadas pero SIN el registro de
version de Alembic (`alembic_version` vacio). En ese estado, un `alembic upgrade
head` normal falla con "relation ... already exists" y el sync automatico se
rompe (era la causa de los runs programados en rojo).

Este script detecta ese caso y lo reconcilia antes de migrar:

- Base ya versionada  -> `upgrade head` normal (aplica migraciones pendientes).
- Base vacia          -> `upgrade head` normal (crea todo desde cero).
- Base POBLADA pero
  SIN version          -> crea las tablas que falten y estampa head (stamp),
                          dejando la base consistente sin recrear lo existente.

Uso: `python scripts/migrate.py`  (desde la raiz del repo).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import inspect, text  # noqa: E402

from app.database import engine, Base  # noqa: E402
from app import models  # noqa: F401, E402  (registra los modelos en Base.metadata)

# Una tabla "nucleo" que siempre existe si el esquema fue creado alguna vez.
_CORE_TABLE = "teams"


def _is_stamped() -> bool:
    """True si existe alembic_version con al menos una fila (base ya versionada)."""
    insp = inspect(engine)
    if "alembic_version" not in insp.get_table_names():
        return False
    with engine.connect() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).first()
    return row is not None


def main() -> None:
    cfg = Config("alembic.ini")
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    stamped = _is_stamped()

    if stamped or _CORE_TABLE not in tables:
        # Estado normal (versionada) o base totalmente vacia: upgrade estandar.
        state = "versionada" if stamped else "vacia"
        print(f"🧬 Migraciones: base {state} -> alembic upgrade head")
        command.upgrade(cfg, "head")
    else:
        # Base POBLADA pero sin sello de version: reconciliar sin recrear.
        print("🩹 Base poblada SIN version de Alembic -> reconciliando "
              "(crea tablas faltantes + stamp head)")
        Base.metadata.create_all(bind=engine)  # crea SOLO lo que falte; no toca lo existente
        command.stamp(cfg, "head")
    print("✅ Migraciones OK")


if __name__ == "__main__":
    main()
