import os
from fastapi import Header, HTTPException

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
