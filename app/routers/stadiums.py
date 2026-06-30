from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter()

@router.get("/stadiums", response_model=list[schemas.StadiumResponse])
def get_stadiums(db: Session = Depends(get_db)):
    return db.query(models.Stadium).all()
