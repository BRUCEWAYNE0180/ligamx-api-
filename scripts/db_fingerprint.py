"""Imprime a que BD apunta DATABASE_URL (sin credenciales) + su huella.

Se usa en los workflows para verificar que GitHub Actions escribe en la MISMA
base que sirve el web service: compara la huella impresa aqui con la que expone
`GET /sync/status` -> database.fingerprint en produccion. Si coinciden, es la
misma base; si no, el secret DATABASE_URL apunta a otra base."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db_identity import db_target, db_fingerprint  # noqa: E402

t = db_target()
print(f"DB target -> dialect={t['dialect']} host={t['host']} dbname={t['dbname']}")
print(f"DB fingerprint -> {db_fingerprint()}")
