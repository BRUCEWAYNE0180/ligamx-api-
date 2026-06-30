from app.database import engine, Base, SessionLocal
from app.services.sync_service import run_sync
from app import models

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
