from datetime import datetime
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def read_root():
    return {"message": "API Liga MX", "version": "1.0", "status": "running"}

@router.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now()}
