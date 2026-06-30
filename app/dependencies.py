import os
from fastapi import Header, HTTPException

SYNC_API_KEY = os.environ.get("SYNC_API_KEY")

def verify_api_key(api_key: str = Header(..., alias="X-API-Key")):
    if api_key != SYNC_API_KEY:
        raise HTTPException(status_code=403, detail="API Key invalida")
    return api_key

def get_or_404(db, model, id_value):
    item = db.query(model).filter(model.id == id_value).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    return item
