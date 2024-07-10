from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette import status
from app.login.auth import JWTBearer
from app.models import QuestionPaper, Section
from app.params import DELETED
from app.subject.basemodel import CreateSection
from database import get_db
from sqlalchemy.orm import joinedload


sectionapiroute = APIRouter(prefix="/section", tags=["section"])


@sectionapiroute.get("/all")
def get_sections(db: Session = Depends(get_db), user_data: dict = Depends(JWTBearer())):
    get_section = db.query(Section).all()
    db.close()
    return get_section

@sectionapiroute.get("/")
def get_section_by_question_paper(question_paper_id:int, db: Session =Depends(get_db), user_data: dict = Depends(JWTBearer())):
    try:
        question_paper = db.query(Section).filter(Section.question_paper_id == question_paper_id, Section.deleted == DELETED).all()
        if not question_paper:
            response = JSONResponse(content={"success": False, "message": "Question Paper not found", "status": status.HTTP_404_NOT_FOUND})
            response.status_code = status.HTTP_404_NOT_FOUND
            return response
        return question_paper
    except Exception as e:
        db.rollback()
        db.close()
        return {"error": str(e)}

@sectionapiroute.post("/create")
def create_section(create_section: CreateSection, db: Session = Depends(get_db), user_data: dict = Depends(JWTBearer())):
    try:
        question_paper = db.query(QuestionPaper).filter(QuestionPaper.id == create_section.question_paper_id, QuestionPaper.deleted == DELETED).first()
        if not question_paper:
            response = JSONResponse(content={"success": False, "message": "Question Paper not found", "status": status.HTTP_404_NOT_FOUND})
            response.status_code = status.HTTP_404_NOT_FOUND
            return response        
        section = Section(name = create_section.name, description = create_section.description, question_paper_id = create_section.question_paper_id, created_by_id=1)
        db.add(section)
        db.commit()
        db.close()
        return {"Message" : "Section Created Successfully"}
    except Exception as e:
        db.rollback()
        db.close()
        return {"error": str(e) }
    

@sectionapiroute.put("/update")
def update_section(section_id: int, update_section: CreateSection, db: Session = Depends(get_db), user_data: dict = Depends(JWTBearer())):
    try:
        sectionId = db.query(Section).filter(Section.id == section_id, Section.deleted== DELETED).first()
        if not sectionId:
            response = JSONResponse(content={"success": False, "message": "Section not found", "status": status.HTTP_404_NOT_FOUND})
            response.status_code = status.HTTP_404_NOT_FOUND
            return response
        question_paper = db.query(QuestionPaper).filter(QuestionPaper.id == update_section.question_paper_id, QuestionPaper.deleted == DELETED).first()
        if not question_paper:
            response = JSONResponse(content={"success": False, "message": "Question Paper not found", "status": status.HTTP_404_NOT_FOUND})
            response.status_code = status.HTTP_404_NOT_FOUND
            return response        
        sectionId.name = update_section.name
        sectionId.description = update_section.description
        sectionId.question_paper_id = update_section.question_paper_id
        db.commit()
        db.close()
        return {"Message" : "Section Updated Successfully"}
    except Exception as e:
        db.rollback()
        db.close()
        return {"error": str(e) }
    

@sectionapiroute.delete("/")
def delete_section(section_id: int, db: Session = Depends(get_db), user_data: dict = Depends(JWTBearer())):
    try:
        section = db.query(Section).filter(Section.id == section_id, Section.deleted == DELETED).first()
        if not section:
            response = JSONResponse(content={"success": False, "message": "Section not found", "status": status.HTTP_404_NOT_FOUND})
            response.status_code = status.HTTP_404_NOT_FOUND
            return response        
        # db.delete(section)
        section.deleted=True
        db.commit()
        db.close()
        return {"Message": " Section Deleted Successfully"}
        
    except Exception as e:
        db.rollback()
        db.close()
        return {"error": str(e)}
