from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import verify_api_key
from app.services.sync_service import run_sync

router = APIRouter()
import os

@router.get("/sync-key-check")
def check_key():
    key = os.environ.get("SYNC_API_KEY")
    return {"has_key": key is not None, "key_length": len(key) if key else 0}

@router.post("/sync")
def sync_data(source: str = "demo", db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    result = run_sync(db, source)
    return {"message": "Datos sincronizados", "source": source, "result": result}
