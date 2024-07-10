from fastapi import APIRouter, Depends, HTTPException
from app.models import IntroText
from app.params import DELETED
from app.questions.basemodel import CreateIntroText
from database import get_db
from sqlalchemy.orm import Session
from starlette import status

introtextroute = APIRouter(prefix="/introtext",tags=["IntroText"])


@introtextroute.get("/")
def get_introtext(db: Session = Depends(get_db)):
    intro_text = db.query(IntroText).filter(IntroText.deleted == DELETED).all()
    db.close()
    return intro_text


@introtextroute.post("/create")
def create_introText(create_intro: CreateIntroText,db : Session = Depends(get_db)):
    try:
        introtextroute = IntroText(name = create_intro.name, type = create_intro.type, created_by_id =1)
        db.add(introtextroute)
        db.commit()
        db.close()
        return {"Message": "Introduction Added Succesfully"}

    except Exception as e:
        db.rollback()
        db.close()
        return {"error": str(e)}
    
@introtextroute.put("/update")
def update_introtext(introText_id:int , update_introText: CreateIntroText, db: Session = Depends(get_db)):
    try:
        intro_text = db.query(IntroText).filter(IntroText.id == introText_id, IntroText.deleted ==DELETED)
        if not intro_text :
            db.close()
            raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= " Introduction Text not found")
        
        intro_text.name = update_introText.name
        intro_text.type = update_introText.type
        db.commit()
        db.close()
        return {"Message": "Introduction Text Updated sucessfully"}
    except Exception as e:
        db.rollback()
        db.close()
        return {"error": str(e)}
    
@introtextroute.delete("/")
def delete_introduction(introductiontext_id: int, db: Session = Depends(get_db)):
    try:
        intro_text_id = db.query(IntroText).filter(IntroText.id == introductiontext_id, IntroText.deleted == DELETED).first()
        if not intro_text_id:
            db.close()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail= "Introduction Text not found")
        intro_text_id.deleted=True
        db.commit()
        db.close()
        return { "Message": "Introduction Deleted Sucessfully"}
    except Exception as e:
        db.rollback()
        db.close()
        return {"error": str(e)}