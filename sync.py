from app.database import engine, Base, SessionLocal
from app.services.sync_service import run_sync
from app import models

# En SQLite (dev) creamos tablas al vuelo; en Postgres el esquema lo maneja
# Alembic (corre `alembic upgrade head` antes de este script en produccion).
if engine.dialect.name == "sqlite":
    Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    result = run_sync(db, "espn")
    print("OK estadios", result["stadiums"], "equipos", result["teams"], "jugadores", result["players"], "partidos", result["matches"])
    print("OK noticias", len(db.query(models.News).all()))
except Exception as e:
    db.rollback()
    print(f"Error durante la sincronizacion: {e}")
    raise
finally:
    db.close()
